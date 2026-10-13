"""Business-day scheduling. Weekday IDs use Sunday=0, matching the client."""
from datetime import date,timedelta
from fastapi import HTTPException

def fail(message): raise HTTPException(422,message)
def calendar(v=None):
    v=[] if v is None else v
    if not isinstance(v,list) or any(type(n) is not int or n<0 or n>6 for n in v) or len(set(v))!=len(v) or len(v)==7: fail('Choose weekly days off, leaving at least one working day.')
    return sorted(v)
def plus(d):
    try: return (date.fromisoformat(d)+timedelta(days=1)).isoformat()
    except (ValueError,OverflowError): fail('Schedule exceeds the supported date range.')
def working(d,off): return (date.fromisoformat(d).weekday()+1)%7 not in off
def business(d,off,strict=False):
    if strict: d=plus(d)
    while not working(d,off): d=plus(d)
    return d
def duration(start,due,off):
    n=0;d=start
    while d<=due:
        if working(d,off): n+=1
        d=plus(d)
    return max(1,n)
def finish(start,n,off):
    d=business(start,off)
    for _ in range(n-1): d=business(d,off,True)
    return d
def normalize_task(t,p):
    off=calendar(p.get('offDays'))
    if t['due']<t['start']: fail('Due date must follow the start date.')
    t['start']=business(t['start'],off);t['due']=business(t['due'],off)
def reschedule(s,before,roots,user,early=False,completion_day=None,calendar_project=None):
    old={t['id']:t for t in before['tasks']};tasks={t['id']:t for t in s['tasks']};projects={p['id']:p for p in s['projects']}
    def children(id): return [t for t in s['tasks'] if t['parentId']==id]
    order=[];seen=set();visiting=set()
    def visit(t):
        if t['id'] in visiting: fail('These relationships would create a cycle.')
        if t['id'] in seen: return
        visiting.add(t['id'])
        for id in t['predecessors']+[c['id'] for c in children(t['id'])]:
            if id not in tasks: fail('Missing dependency.')
            visit(tasks[id])
        visiting.remove(t['id']);seen.add(t['id']);order.append(t)
    for t in s['tasks']: visit(t)
    affected=set(roots);changed=[]
    def pct(t): return max(pct(c) for c in children(t['id'])) if children(t['id']) else t['progress']
    def allowed(t): return user['role']=='admin' or user['role']=='head' and user['department']==projects[t['projectId']]['department'] or early and user['role']=='delegate' and any(tasks[id]['projectId']==t['projectId'] for id in roots)
    def complete(t): return all(complete(c) for c in children(t['id'])) if children(t['id']) else t['progress']==100
    def end(t):
        if early and t['id'] in roots and completion_day: return completion_day
        cs=children(t['id'])
        if cs and all(complete(c) for c in cs): return max(end(c) for c in cs)
        return effective_finish(s,t)
    for t in order:
        p=projects[t['projectId']];off=calendar(p.get('offDays'));prior=old.get(t['id'],t);cs=children(t['id']);start=t['start'];due=t['due']
        if cs:
            if any(c['id'] in affected for c in cs):
                start=min([start]+[c['start'] for c in cs]);due=max([due]+[c['due'] for c in cs]);affected.add(t['id'])
        elif t['id'] not in roots and (any(id in affected for id in t['predecessors']) or calendar_project==t['projectId']):
            if pct(t)>0:
                if any(end(tasks[id])>=t['start'] for id in t['predecessors']): fail('A successor has already started. Resolve its dates before changing this plan.')
                continue
            prior_p=next((x for x in before['projects'] if x['id']==p['id']),p)
            n=duration(prior['start'],prior['due'],prior_p.get('offDays',[]));pred_end=max([end(tasks[id]) for id in t['predecessors']],default=None)
            start=business(pred_end,off,True) if pred_end else business(t['start'],off)
            if start<p['start']: start=business(p['start'],off)
            if early and start>=t['start']: continue
            due=finish(start,n,off);affected.add(t['id'])
        if start!=t['start'] or due!=t['due']:
            if not allowed(t): fail('This change affects another department. Ask an administrator to reschedule the full chain.')
            changed.append(dict(taskId=t['id'],fromStart=t['start'],fromDue=t['due'],start=start,due=due));t['start']=start;t['due']=due
    for p in s['projects']:
        ts=[t for t in s['tasks'] if t['projectId']==p['id']]
        if ts: p['start']=min([p['start']]+[t['start'] for t in ts]);p['due']=max([p['due']]+[t['due'] for t in ts])
    for t in s['tasks']:
        if t['id'] in affected and any(end(tasks[id])>=t['start'] for id in t['predecessors']): fail('The schedule conflicts with a predecessor.')
    return changed
def schedule_audit(changes): return ' · Auto-rescheduled '+str(len(changes))+' tasks' if changes else ''

def effective_finish(s,t):
    from datetime import datetime
    from zoneinfo import ZoneInfo
    def complete(task):
        cs=[c for c in s['tasks'] if c['parentId']==task['id']]
        return all(complete(c) for c in cs) if cs else task['progress']==100
    cs=[c for c in s['tasks'] if c['parentId']==t['id']]
    if cs and all(complete(c) for c in cs): return max(effective_finish(s,c) for c in cs)
    u=next((u for u in s['updates'] if u['taskId']==t['id'] and u['progress']==100),None) if t['progress']==100 else None
    return datetime.fromisoformat(u['createdAt'].replace('Z','+00:00')).astimezone(ZoneInfo('Asia/Amman')).date().isoformat() if u else t['due']
