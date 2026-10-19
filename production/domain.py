from .commercial import with_finance,ACTIONS,mutate_commercial,project_commercial,amount_in,invoice_term,invoice_change
from .scheduling import calendar,normalize_task,reschedule,schedule_audit,effective_finish
from .access import with_access,can_see,project_for_action
"""Validated application commands shared by every Python API write path."""
from copy import deepcopy
import re
from .catalogs import catalog_rows,allowed,KINDS
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from uuid import uuid4
from zoneinfo import ZoneInfo
from fastapi import HTTPException
DEPARTMENTS=['Digital & IT','Warehouse','Production','Quality','HR','Engineering']
ROLES=['admin','management','executive','head','delegate','finance']
def reject(message, status=422): raise HTTPException(status, message)
def text(v,label,limit=180):
    if not isinstance(v,str) or not v.strip() or len(v.strip())>limit: reject(f'{label} is required (maximum {limit} characters).')
    return v.strip()
def number(v,label,lo,hi):
    if isinstance(v,bool) or not isinstance(v,(int,float,Decimal)): reject(f'{label} must be numeric.')
    try: n=Decimal(str(v))
    except InvalidOperation: reject(f'{label} must be numeric.')
    if not n.is_finite() or not Decimal(str(lo))<=n<=Decimal(str(hi)): reject(f'{label} must be between {lo} and {hi}.')
    return float(n)
def amount(v,label): return float(Decimal(str(number(v,label,.01,1e10))).quantize(Decimal('.01'),rounding=ROUND_HALF_UP))
def valid_date(v,label):
    try:
        if not isinstance(v,str) or len(v)!=10 or date.fromisoformat(v).isoformat()!=v: raise ValueError()
    except ValueError: reject(f'{label} must be a valid date.')
    return v
def today(): return datetime.now(ZoneInfo('Asia/Amman')).date().isoformat()
def can_plan(u,dept): return u['role']=='admin' or u['role']=='head' and u['department']==dept
def authorize(ok):
    if not ok: reject('Your role does not allow this action.',403)
def leaf_tasks(s,project=None,parent=None):
    ts=[t for t in s['tasks'] if not project or t['projectId']==project]
    if parent:
        ids={parent}
        while True:
            nxt=ids|{t['id'] for t in ts if t['parentId'] in ids}
            if nxt==ids: break
            ids=nxt
        ts=[t for t in ts if t['id'] in ids]
    return [t for t in ts if not any(c['parentId']==t['id'] for c in s['tasks'])]
def progress(s,parent):
    ts=leaf_tasks(s,parent=parent);w=sum(t['effort'] for t in ts)
    return sum(t['effort']*t['progress'] for t in ts)/w if w else 0

def mutate(state,user,action,b):
    authorize(user['role']!='management')
    s=with_finance(with_access(deepcopy(state)));s['catalogs']=catalog_rows(s);uid=str(uuid4());label='';audit_project=project_for_action(s,action,b);audit_project_id=audit_project['id'] if audit_project else None
    if action in ['task','update','po','invoice','payment','project_access','baseline','project_dates','project_calendar']+[a for a in ACTIONS if a!='consultant']: authorize(action=='change_decision' and user['role']=='finance' or can_see(s,user,audit_project))
    if action in ACTIONS:
        s,label=mutate_commercial(s,user,action,b,uid,today())
    elif action=='baseline':
        p=audit_project;authorize(p and can_plan(user,p['department']))
        tasks=[t for t in s['tasks'] if t['projectId']==p['id']]
        if not tasks: reject('Add a task plan before saving a baseline.')
        baselines=s.setdefault('baselines',[]);version=max([x['version'] for x in baselines if x['projectId']==p['id']]+[0])+1
        baseline=dict(id=uid,projectId=p['id'],version=version,name=text(b.get('name'),'Baseline name',80),reason=text(b.get('reason'),'Baseline reason',500),createdById=user['id'],createdBy=user['name'],createdAt=datetime.now(timezone.utc).isoformat(),title=p['title'],start=p['start'],due=p['due'],tasks=[dict(taskId=t['id'],parentId=t['parentId'],title=t['title'],start=t['start'],due=t['due'],effort=t['effort'],isMilestone=bool(t.get('isMilestone'))) for t in tasks])
        baselines.append(baseline);label=f"Saved baseline v{version} · {p['title']} · {baseline['name']}"
    elif action=='project_calendar':
        p=audit_project;authorize(p and can_plan(user,p['department']));reason=text(b.get('reason'),'Calendar change reason',300);p['offDays']=calendar(b.get('offDays'))
        changes=reschedule(s,state,[],user,calendar_project=p['id']);label=f"Updated working week · {p['title']} · days off {p['offDays']} · {reason}"+schedule_audit(changes)
    elif action=='project_dates':
        p=audit_project;authorize(p and can_plan(user,p['department']))
        start=valid_date(b.get('start'),'Start');due=valid_date(b.get('due'),'Due date');reason=text(b.get('reason'),'Schedule change reason',300)
        if due<start or any(t['projectId']==p['id'] and (t['start']<start or t['due']>due) for t in s['tasks']): reject('Project dates must contain every task.')
        label=f"Revised project dates · {p['start']}–{p['due']} → {start}–{due} · {reason}";p['start']=start;p['due']=due
    elif action=='master':
        authorize(user['role']=='admin')
        old=next((m for m in s['masterProjects'] if m['id']==b.get('id')),None)
        if b.get('id') and not old: reject('Master project not found.')
        m=dict(id=old['id'] if old else uid,title=text(b.get('title'),'Master project name',100),primaryDepartment=b.get('primaryDepartment'),owner=text(b.get('owner'),'Accountable lead',80),description=str(b.get('description',''))[:1000])
        if not allowed(s,'department',m['primaryDepartment'],old.get('primaryDepartment') if old else None): reject('Select an active primary department.')
        if any(x['id']!=m['id'] and x['title'].lower()==m['title'].lower() for x in s['masterProjects']): reject('A master project with this name already exists.')
        s['masterProjects']=[m if x['id']==m['id'] else x for x in s['masterProjects']] if old else s['masterProjects']+[m]
        label=('Updated' if old else 'Created')+' master project · '+m['title']
    elif action=='project_access':
        authorize(user['role']=='admin');p=next((p for p in s['projects'] if p['id']==b.get('id')),None)
        if not p: reject('Subproject not found.')
        group_ids=b.get('accessGroupIds')
        if not isinstance(group_ids,list) or any(not isinstance(g,str) or not any(c['kind']=='department' and c['id']==g for c in s['catalogs']) for g in group_ids): reject('Select valid department groups.')
        p['accessGroupIds']=list(dict.fromkeys(group_ids));label='Updated project access · '+p['title']
    elif action=='catalog':
        authorize(user['role']=='admin')
        old=next((x for x in s['catalogs'] if x['id']==b.get('id')),None)
        if b.get('id') and not old: reject('Dropdown value not found.')
        kind=b.get('kind')
        if kind not in KINDS or old and old['kind']!=kind: reject('Select a valid dropdown.')
        name=text(b.get('name'),'Name',60 if kind=='department' else 80 if kind=='resource' else 100)
        if not isinstance(b.get('active'),bool): reject('Active must be true or false.')
        if any(x['kind']==kind and (not old or x['id']!=old['id']) and x['name'].lower()==name.lower() for x in s['catalogs']): reject('This name already exists in this dropdown.')
        if kind=='department' and not b['active'] and not any(x['kind']==kind and x['active'] and (not old or x['id']!=old['id']) for x in s['catalogs']): reject('Keep at least one active department.')
        if old and kind=='department' and old['name']!=name:
            for key in ['projects','tasks','users']:
                for row in s[key]:
                    if row['department']==old['name']: row['department']=name
            for master in s['masterProjects']:
                if master.get('primaryDepartment')==old['name']: master['primaryDepartment']=name
        if old and old['name']!=name and kind in ['vendor','resource']:
            for item in s['pos' if kind=='vendor' else 'tasks']:
                if item[kind]==old['name']: item[kind]=name
        row=dict(id=old['id'] if old else uid,kind=kind,name=name,active=b['active'])
        s['catalogs']=[row if x['id']==row['id'] else x for x in s['catalogs']] if old else s['catalogs']+[row]
        label=('Updated' if old else 'Added')+' '+kind+' · '+(old['name']+' → ' if old and old['name']!=name else '')+name+('' if row['active'] else ' (inactive)')
    elif action=='user_edit':
        authorize(user['role']=='admin')
        old=next((x for x in s['users'] if x['id']==b.get('id')),None)
        if not old: reject('Account not found.')
        u={**old,'name':text(b.get('name'),'Name',80),'email':text(b.get('email'),'Email',254).lower(),'role':b.get('role'),'department':b.get('department'),'active':b.get('active')}
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',u['email']): reject('Enter a valid email address.')
        if u['role'] not in ROLES or not isinstance(u['active'],bool): reject('Select a valid role and account status.')
        if not allowed(s,'department',u['department'],old['department']): reject('Select an active department.')
        if any(x['id']!=u['id'] and x['email'].lower()==u['email'] for x in s['users']): reject('An account with this email already exists.')
        if u['id']==user['id'] and (not u['active'] or u['role']!='admin'): reject('You cannot disable or demote your own administrator account.')
        if old['active'] and old['role']=='admin' and (not u['active'] or u['role']!='admin') and not any(x['id']!=u['id'] and x['active'] and x['role']=='admin' for x in s['users']): reject('Keep at least one active administrator.')
        if u['active'] and any(t['assigneeId']==u['id'] and t['progress']<100 and u['role'] not in ['admin','head','delegate'] for t in s['tasks']): reject('Reassign this account’s open tasks before changing its role.')
        s['users']=[u if x['id']==u['id'] else x for x in s['users']];label='Updated account · '+u['name']+' · '+u['role']+' · '+('active' if u['active'] else 'disabled')
    elif action=='project':
        authorize(user['role']=='admin' or user['role']=='head' and user['department']==b.get('department'))
        p=dict(id=uid,createdById=user['id'],accessGroupIds=[],offDays=calendar(b.get('offDays')),masterId=b.get('masterId'),title=text(b.get('title'),'Project title',100),department=b.get('department'),owner=text(b.get('owner'),'Project lead',80),budget=number(b.get('budget'),'Budget',0,1e10),start=valid_date(b.get('start'),'Start'),due=valid_date(b.get('due'),'Due'),description=str(b.get('description',''))[:1000],color='#b31c3f')
        if not any(m['id']==p['masterId'] for m in s['masterProjects']): reject('Select a valid master project.')
        if not allowed(s,'department',p['department']): reject('Select a valid department.')
        if p['due']<p['start']: reject('Due date must follow the start date.')
        p.update(project_commercial(s,b,p,today()));p['budget']=amount_in(p['budget'],p,'Budget')
        s['projects'].append(p);audit_project_id=p['id'];label='Created subproject · '+p['title']
    elif action=='task':
        p=next((p for p in s['projects'] if p['id']==b.get('projectId')),None)
        if not p: reject('Select a valid subproject.')
        authorize(can_plan(user,p['department']))
        old=next((t for t in s['tasks'] if t['id']==b.get('id')),None)
        if b.get('id') and not old: reject('Task not found.')
        if old and old['projectId']!=p['id']: reject('Tasks cannot move between subprojects.')
        preds=b.get('predecessors',[])
        if not isinstance(preds,list) or any(not isinstance(x,str) for x in preds): reject('Invalid predecessors.')
        hidden_preds=[pred for pred in old['predecessors'] if not can_see(s,user,project_for_action(s,'update',{'taskId':pred}))] if old else []
        preds=list(dict.fromkeys(preds+hidden_preds))
        t=dict(id=old['id'] if old else uid,projectId=p['id'],title=text(b.get('title'),'Task title'),department=p['department'],parentId=b.get('parentId') or None,predecessors=list(dict.fromkeys(preds)),assigneeId=b.get('assigneeId') or None,resource=text(b.get('resource') or (old['resource'] if old else 'Unassigned'),'Resource',80),effort=number(b.get('effort'),'Planned hours',1,100000),start=valid_date(b.get('start'),'Start'),due=valid_date(b.get('due'),'Due'),progress=old['progress'] if old else 0,blocked=old['blocked'] if old else False,isMilestone=b.get('isMilestone',bool(old.get('isMilestone')) if old else False))
        if old and old.get('isMilestone') and not t['isMilestone'] and any(x.get('milestoneId')==t['id'] and not x['cancelled'] for x in s['paymentTerms']): reject('This milestone is used by a payment condition.')
        if type(t['isMilestone']) is not bool: reject('Milestone must be true or false.')
        if not old or old['start']!=t['start'] or old['due']!=t['due']: normalize_task(t,p)
        date_changed=old and (old['start']!=t['start'] or old['due']!=t['due'])
        reason=text(b.get('changeReason'),'Schedule change reason',300) if date_changed and any(x['projectId']==p['id'] for x in s.get('baselines',[])) else ''
        if not allowed(s,'resource',t['resource'],old['resource'] if old else None): reject('Select an active resource team.')
        if t['due']<t['start'] or t['start']<p['start']: reject('Task dates must be within the subproject dates.')
        parent=next((x for x in s['tasks'] if x['id']==t['parentId']),None)
        if t['parentId'] and (not parent or parent['projectId']!=p['id'] or parent['id']==t['id']): reject('Select a valid parent task.')
        if parent and (parent['progress']>0 or parent['predecessors']): reject('Add subtasks only to a parent with no progress or predecessors.')
        if t['assigneeId'] and not any(u['id']==t['assigneeId'] and u['active'] and u['role'] in ['admin','head','delegate'] for u in s['users']): reject('Select an active account.')
        for pred in t['predecessors']:
            pt=next((x for x in s['tasks'] if x['id']==pred),None)
            if not pt or pred==t['id']: reject('Invalid predecessor.')
            if pred not in hidden_preds: authorize(can_see(s,user,project_for_action(s,'update',{'taskId':pred})))
            if next(x['masterId'] for x in s['projects'] if x['id']==pt['projectId'])!=p['masterId']: reject('Predecessors must belong to the same master project.')
            if effective_finish(s,pt)>=t['start']: reject('Finish-to-start requires a later start than predecessor completion.')
        s['tasks']=[t if x['id']==t['id'] else x for x in s['tasks']] if old else s['tasks']+[t]
        for x in s['tasks']:
            if x['parentId']==t['id'] and (x['start']<t['start'] or x['due']>t['due']): reject('Parent dates must contain its subtasks.')
        graph={x['id']:x['predecessors']+[c['id'] for c in s['tasks'] if c['parentId']==x['id']] for x in s['tasks']};visiting=set();visited=set()
        def visit(k):
            if k in visiting: reject('These relationships would create a cycle.')
            if k in visited: return
            visiting.add(k)
            for v in graph.get(k,[]): visit(v)
            visiting.remove(k);visited.add(k)
        for k in graph: visit(k)
        changes=reschedule(s,state,[t['id']],user) if date_changed or not old or old['predecessors']!=t['predecessors'] else []
        label=(f"Revised task dates · {old['start']}–{old['due']} → {t['start']}–{t['due']}"+(' · '+reason if reason else '')) if date_changed else ('Updated' if old else 'Created')+' task · '+t['title']
        label+=schedule_audit(changes)
    elif action=='update':
        t=next((x for x in s['tasks'] if x['id']==b.get('taskId')),None)
        if not t: reject('Task not found.')
        authorize(can_plan(user,t['department']) or user['role']=='delegate' and t['assigneeId']==user['id'])
        if any(x['parentId']==t['id'] for x in s['tasks']): reject('Update subtasks; summary progress rolls up automatically.')
        pct=number(b.get('progress'),'Progress',0,100);note=text(b.get('note'),'Update note',2000)
        if pct!=int(pct) or type(b.get('blocked')) is not bool: reject('Invalid progress or blocked status.')
        if pct>0 and any(progress(s,p)<100 for p in t['predecessors']): reject('Complete all predecessors before recording progress.')
        if pct<100 and t['progress']==100 and any(t['id'] in x['predecessors'] and progress(s,x['id'])>0 for x in s['tasks']): reject('A successor has already started.')
        if 'rescheduleSuccessors' in b and type(b['rescheduleSuccessors']) is not bool: reject('Choose whether to reschedule successors.')
        early=pct==100 and t['progress']<100 and today()<t['due']
        if b.get('rescheduleSuccessors') and not early: reject('Only newly completed early tasks can bring successors forward.')
        if early and b.get('rescheduleSuccessors'): t['progress']=int(pct)
        changes=reschedule(s,state,[t['id']],user,early=True,completion_day=today()) if early and b.get('rescheduleSuccessors') else []
        t['progress']=int(pct);t['blocked']=False if pct==100 else b['blocked']
        s['updates'].insert(0,dict(id=uid,taskId=t['id'],progress=int(pct),note=note,author=user['name'],authorId=user['id'],createdAt=datetime.now(timezone.utc).isoformat()))
        label=f"Updated progress · {t['title']} → {int(pct)}%"+(" · Early completion: reschedule confirmed" if b.get("rescheduleSuccessors") else " · Early completion: retained dates" if early else "")+schedule_audit(changes)
    elif action=='po':
        authorize(user['role'] in ['admin','finance']);p=next((p for p in s['projects'] if p['id']==b.get('projectId')),None)
        if not p: reject('Select a valid subproject.')
        po=dict(id=uid,projectId=p['id'],number=text(b.get('number'),'PO number',60),vendor=text(b.get('vendor'),'Vendor',100),amount=amount_in(b.get('amount'),p,'PO amount',.0001),date=valid_date(b.get('date'),'PO date'),description=text(b.get('description'),'Description',300))
        if not allowed(s,'vendor',po['vendor']): reject('Select an active vendor.')
        if any(x['number'].lower()==po['number'].lower() for x in s['pos']): reject('This PO number already exists.')
        if sum(Decimal(str(x['amount'])) for x in s['pos'] if x['projectId']==p['id'])+Decimal(str(po['amount']))>Decimal(str(p['budget'])): reject('This PO exceeds the available project budget.')
        s['pos'].append(po);label='Created PO · '+po['number']
    elif action=='invoice':
        authorize(user['role'] in ['admin','finance']);po=next((p for p in s['pos'] if p['id']==b.get('poId')),None)
        if not po: reject('Select a valid purchase order.')
        i=dict(id=uid,poId=po['id'],number=text(b.get('number'),'Invoice number',60),amount=amount_in(b.get('amount'),next(p for p in s['projects'] if p['id']==po['projectId']),'Invoice amount',.0001),date=valid_date(b.get('date'),'Invoice date'),due=valid_date(b.get('due'),'Due date'),status='Unpaid')
        if i['due']<i['date'] or i['date']<po['date']: reject('Check invoice and payment dates against the PO date.')
        if any(x['poId']==po['id'] and x['number'].lower()==i['number'].lower() for x in s['invoices']): reject('Invoice number already exists for this PO.')
        if sum(Decimal(str(x['amount'])) for x in s['invoices'] if x['poId']==po['id'])+Decimal(str(i['amount']))>Decimal(str(po['amount'])): reject('Total invoices cannot exceed the purchase order amount.')
        i['changeRequestId']=invoice_change(s,b,po,i['amount']);i['termId']=invoice_term(s,b,po,i['amount']);s['invoices'].append(i);label='Recorded invoice · '+i['number']
    elif action=='payment':
        authorize(user['role'] in ['admin','finance']);i=next((x for x in s['invoices'] if x['id']==b.get('invoiceId')),None)
        if not i: reject('Invoice not found.')
        if i['status']=='Paid': reject('Invoice is already paid.')
        i['reference']=text(b.get('reference'),'Payment reference',100);i['paidDate']=valid_date(b.get('paidDate'),'Payment date')
        if i['paidDate']<i['date'] or i['paidDate']>today(): reject('Payment date must be between invoice date and today.')
        i['status']='Paid';label='Recorded payment · '+i['number']
    else: reject('Unknown action.')
    for task in s['tasks']:
        prior=next((x for x in state['tasks'] if x['id']==task['id']),None)
        if prior and (prior['start']!=task['start'] or prior['due']!=task['due']):
            s['audit'].insert(0,dict(id=str(uuid4()),projectId=task['projectId'],actorId=user['id'],actor=user['name'],role=user['role'],action=f"Schedule · {task['title']} · {prior['start']}–{prior['due']} → {task['start']}–{task['due']}",at=datetime.now(timezone.utc).isoformat()))
    s['audit'].insert(0,dict(id=uid,projectId=audit_project_id,actorId=user['id'],actor=user['name'],role=user['role'],action=label,at=datetime.now(timezone.utc).isoformat()));return s
