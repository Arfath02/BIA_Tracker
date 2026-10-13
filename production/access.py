from .masters import with_masters
from .catalogs import catalog_rows

def with_access(state):
    s=with_masters(state)
    return {**s,'projects':[{**p,'createdById':p.get('createdById'),'accessGroupIds':p.get('accessGroupIds',[])} for p in s['projects']]}
def groups(s):
    return [dict(id=d['id'],name=d['name'],active=d['active'],memberIds=[u['id'] for u in s['users'] if u['active'] and u['department']==d['name']]) for d in catalog_rows(s) if d['kind']=='department']
def can_see(s,u,p):
    if not u or not p: return False
    if u['role'] in ['admin','management'] or p.get('createdById')==u['id'] or u['role']=='head' and p['department']==u['department']: return True
    if any(t['projectId']==p['id'] and t['assigneeId']==u['id'] for t in s['tasks']): return True
    group=next((d for d in catalog_rows(s) if d['kind']=='department' and d['name']==u['department']),None)
    return bool(group and group['id'] in p.get('accessGroupIds',[]))
def project_for_action(s,action,b):
    project_id=b.get('projectId') if action in ['task','po','baseline','project_dates','project_calendar'] else b.get('id') if action=='project_access' else None
    if action=='update': project_id=next((t['projectId'] for t in s['tasks'] if t['id']==b.get('taskId')),None)
    if action in ['invoice','payment']:
        po_id=b.get('poId') if action=='invoice' else next((i['poId'] for i in s['invoices'] if i['id']==b.get('invoiceId')),None)
        project_id=next((p['projectId'] for p in s['pos'] if p['id']==po_id),None)
    return next((p for p in s['projects'] if p['id']==project_id),None)
def completed(s,task_id):
    children=[t for t in s['tasks'] if t['parentId']==task_id]
    return all(completed(s,t['id']) for t in children) if children else any(t['id']==task_id and t['progress']==100 for t in s['tasks'])
def visible_state(state,user):
    s=with_access(state);department_groups=groups(s)
    if user['role']=='admin': return {**s,'departmentGroups':department_groups,'managementGroup':dict(id='management',name='Management',memberIds=[u['id'] for u in s['users'] if u['active'] and u['role']=='management'])}
    projects=[p for p in s['projects'] if can_see(s,user,p)];project_ids={p['id'] for p in projects};master_ids={p['masterId'] for p in projects}
    tasks=[t for t in s['tasks'] if t['projectId'] in project_ids];task_ids={t['id'] for t in tasks};pos=[p for p in s['pos'] if p['projectId'] in project_ids];po_ids={p['id'] for p in pos}
    members={user['id']}|{p.get('createdById') for p in projects}|{t['assigneeId'] for t in tasks}
    return {**s,'baselines':[b for b in s.get('baselines',[]) if b['projectId'] in project_ids],'masterProjects':[m for m in s['masterProjects'] if user['role']=='management' or m['id'] in master_ids],'projects':projects,'tasks':[{**t,'predecessors':[p for p in t['predecessors'] if p in task_ids],'externalPredecessorCount':sum(p not in task_ids for p in t['predecessors']),'externalPredecessorsPending':sum(p not in task_ids and not completed(s,p) for p in t['predecessors'])} for t in tasks],'pos':pos,'invoices':[i for i in s['invoices'] if i['poId'] in po_ids],'updates':[u for u in s['updates'] if u['taskId'] in task_ids],'audit':[a for a in s['audit'] if a.get('projectId') in project_ids or not a.get('projectId') and a.get('actorId')==user['id']],'users':[u for u in s['users'] if u['id'] in members or u['role']=='admin' or user['role']=='head' and u['department']==user['department']],'departmentGroups':[{**g,'memberIds':[m for m in g['memberIds'] if m in members]} for g in department_groups if g['name']==user['department']]}
