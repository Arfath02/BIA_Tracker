import os,json,tempfile
from pathlib import Path
os.environ['BIA_TESTING']='1'
os.environ['DATABASE_URL']='sqlite:///'+str(Path(tempfile.mkdtemp())/'test.db')
os.environ['TRUSTED_ORIGINS']='http://testserver'
from fastapi.testclient import TestClient
from sqlalchemy import insert,select
from production import database as d
from production.app import app,engine,ph

def setup_module():
    from production.migrations import initialize
    initialize(engine)
    with engine.begin() as db:
        d.insert_user(db,dict(id='admin',email='admin@example.test',name='Admin',role='admin',department='Digital & IT',active=True,password_hash=ph.hash('Only-local-test-password')))
        original=d.read_state(db);demo=json.loads(Path('production/seed.json').read_text());demo['users']=original['users']
        from production.catalogs import catalog_rows
        demo['catalogs']=catalog_rows(demo)
        d.persist_changes(db,original,demo)

def client(): return TestClient(app,headers={'Origin':'http://testserver','X-BIA-Request':'1'})
def admin():
    c=client();assert c.post('/api/login',json={'email':'admin@example.test','password':'Only-local-test-password'}).status_code==200;return c

def test_unauthenticated_data_protected():
    c=client();assert c.get('/api/state').json()['projects']==[]
    assert c.post('/api/mutate',json={'action':'update','version':1,'payload':{}}).status_code==401

def test_shared_update_and_conflict():
    c=admin();s=c.get('/api/state').json();r=c.post('/api/mutate',json={'action':'update','version':s['version'],'payload':{'taskId':'wf2','progress':75,'blocked':False,'note':'Validated progress'}});assert r.status_code==200,r.text
    assert c.post('/api/mutate',json={'action':'update','version':s['version'],'payload':{'taskId':'wf2','progress':80,'blocked':False,'note':'Stale'}}).status_code==409
    assert next(t for t in admin().get('/api/state').json()['tasks'] if t['id']=='wf2')['progress']==75

def test_head_scope_and_delegate_assignment():
    c=admin()
    for name,role in [('Head','head'),('Delegate','delegate'),('Executive','executive')]:
        assert c.post('/api/users',json={'name':name,'email':name.lower()+'@example.test','password':'Only-local-test-password','role':role,'department':'HR'}).status_code==200
    h=client();h.post('/api/login',json={'email':'head@example.test','password':'Only-local-test-password'})
    s=c.get('/api/state').json();delegate=next(u for u in s['users'] if u['role']=='delegate');task=next(t for t in s['tasks'] if t['id']=='wf2')
    task['assigneeId']=delegate['id'];assert h.post('/api/mutate',json={'action':'task','version':s['version'],'payload':task}).status_code==200
    s=h.get('/api/state').json();assert h.post('/api/mutate',json={'action':'update','version':s['version'],'payload':{'taskId':'qa2','progress':40,'blocked':False,'note':'Should fail'}}).status_code==403
    assert h.post('/api/users',json={'name':'Escalated','email':'bad@example.test','password':'Only-local-test-password','role':'admin','department':'HR'}).status_code==403
    member=client();member.post('/api/login',json={'email':'delegate@example.test','password':'Only-local-test-password'})
    assert member.post('/api/mutate',json={'action':'update','version':s['version'],'payload':{'taskId':'wf2','progress':80,'blocked':False,'note':'Assigned work'}}).status_code==200
    c.post('/api/users/active',json={'id':delegate['id'],'active':False})
    assert member.post('/api/mutate',json={'action':'update','version':s['version'],'payload':{}}).status_code==401

def test_finance_constraints_and_atomicity():
    c=admin();s=c.get('/api/state').json()
    r=c.post('/api/mutate',json={'action':'invoice','version':s['version'],'payload':{'poId':'po1','number':'BAD','amount':99999999,'date':'2026-09-29','due':'2026-10-01'}})
    assert r.status_code==422
    assert c.get('/api/state').json()['version']==s['version']

def test_csrf_and_no_http_bootstrap():
    c=client();assert c.post('/api/login',json={'email':'admin@example.test','password':'Only-local-test-password'},headers={'Origin':'https://evil.example'}).status_code==403
    assert c.post('/api/setup',json={}).status_code==403

def test_no_password_hashes_and_append_only_audit():
    c=admin();s=c.get('/api/state').json();assert 'password_hash' not in json.dumps(s)
    assert any('Updated progress' in x['action'] for x in s['audit'])
    assert s['updates'][0]['note'] in ['Assigned work','Validated progress']

def test_sqlserver_schema_compiles():
    from sqlalchemy.schema import CreateTable
    from sqlalchemy.dialects import mssql
    for table in d.metadata.sorted_tables: assert str(CreateTable(table).compile(dialect=mssql.dialect()))

def test_admin_catalogs_and_account_changes():
    c=admin()
    def change(action,payload):
        s=c.get('/api/state').json()
        return c.post('/api/mutate',json={'version':s['version'],'action':action,'payload':payload})
    assert change('catalog',{'kind':'department','name':'Sales','active':True}).status_code==200
    assert change('catalog',{'kind':'department','name':'sAlEs','active':True}).status_code==422
    s=c.get('/api/state').json();hr=next(x for x in s['catalogs'] if x['name']=='HR')
    h=client();h.post('/api/login',json={'email':'head@example.test','password':'Only-local-test-password'})
    assert h.post('/api/mutate',json={'version':s['version'],'action':'catalog','payload':{'kind':'vendor','name':'Forbidden','active':True}}).status_code==403
    assert change('catalog',{**hr,'name':'People'}).status_code==200
    s=c.get('/api/state').json();assert all(x['department']!='HR' for key in ['projects','tasks','users'] for x in s[key]);assert h.get('/api/state').json()['user'] is None
    assert c.post('/api/users',json={'name':'New','email':'new@example.test','role':'delegate','department':'People','password':'Only-local-test-password','version':s['version']}).status_code==200
    assert c.post('/api/users',json={'name':'Stale','email':'stale@example.test','role':'delegate','department':'People','password':'Only-local-test-password','version':s['version']}).status_code==409
    assert change('catalog',{**hr,'name':'People','active':False}).status_code==200
    assert c.post('/api/users',json={'name':'Bad','email':'inactive@example.test','role':'delegate','department':'People','password':'Only-local-test-password'}).status_code==422
    s=c.get('/api/state').json();u=next(x for x in s['users'] if x['email']=='new@example.test')
    assert change('user_edit',{**u,'name':'Renamed user'}).status_code==200
    assert change('user_edit',{**s['user'],'active':False}).status_code==422
    account=client();assert account.post('/api/login',json={'email':'new@example.test','password':'Only-local-test-password'}).status_code==200
    s=c.get('/api/state').json();assert c.post('/api/users/reset-password',json={'id':u['id'],'password':'Replacement-test-password','version':s['version']}).status_code==200
    assert account.get('/api/state').json()['user'] is None
    assert account.post('/api/login',json={'email':'new@example.test','password':'Only-local-test-password'}).status_code==401
    assert account.post('/api/login',json={'email':'new@example.test','password':'Replacement-test-password'}).status_code==200

def test_connection_builder_encodes_special_password_characters():
    from deploy.configure import connection_url
    from sqlalchemy.engine import make_url
    original='special@:/?#$ password\\value'
    parsed=make_url(connection_url('sql.internal','1433','BIA_Transformation','bia@runtime',original))
    assert parsed.password==original and parsed.username=='bia@runtime'
    assert parsed.query['Encrypt']=='yes' and parsed.query['TrustServerCertificate']=='no'

def test_multiple_masters_hierarchy_and_permissions():
    c=admin()
    def change(action,payload):
        s=c.get('/api/state').json()
        return c.post('/api/mutate',json={'version':s['version'],'action':action,'payload':payload})
    s=c.get('/api/state').json();assert all(p['masterId']=='bia-digital-transformation' for p in s['projects'])
    r=change('master',{'title':'Factory expansion','owner':'Engineering','primaryDepartment':'Engineering','description':'Capital works'});assert r.status_code==200,r.text
    master_id=r.json()['masterId'];assert change('master',{'title':'FACTORY EXPANSION','owner':'Lead','primaryDepartment':'Engineering'}).status_code==422
    project={'masterId':master_id,'title':'Civil works','department':'Engineering','owner':'Lead','budget':10000,'start':'2026-09-30','due':'2026-12-31'}
    assert change('project',{**project,'masterId':'invalid'}).status_code==422
    assert change('project',project).status_code==200
    s=c.get('/api/state').json();project_id=next(x['id'] for x in s['projects'] if x['title']=='Civil works')
    task={'projectId':project_id,'title':'Foundation','resource':'Unassigned','effort':20,'start':'2026-09-30','due':'2026-10-30','predecessors':['wf1']}
    assert change('task',task).status_code==422
    assert change('task',{**task,'predecessors':[]}).status_code==200
    assert change('master',{'id':master_id,'title':'Plant expansion','owner':'Lead','primaryDepartment':'Engineering'}).status_code==200
    s=c.get('/api/state').json();assert len(s['masterProjects'])==2;assert next(p for p in s['projects'] if p['id']==project_id)['masterId']==master_id
    executive=client();executive.post('/api/login',json={'email':'executive@example.test','password':'Only-local-test-password'})
    assert executive.post('/api/mutate',json={'version':s['version'],'action':'master','payload':{'title':'Not allowed','owner':'Lead'}}).status_code==403
    with engine.connect() as db:
        assert db.execute(select(d.projects.c.masterId).where(d.projects.c.id==project_id)).scalar_one()==master_id
        assert db.execute(select(d.masters.c.title).where(d.masters.c.id==master_id)).scalar_one()=='Plant expansion'

def test_department_access_grants_revocation_and_hidden_dependencies():
    c=admin()
    def change(who,action,payload,expected=200):
        s=who.get('/api/state').json();r=who.post('/api/mutate',json={'version':s['version'],'action':action,'payload':payload});assert r.status_code==expected,r.text;return r
    members={}
    for name,role in [('AccessFinance','finance'),('AccessDelegate','delegate'),('AccessHead','head')]:
        assert c.post('/api/users',json={'name':name,'email':name.lower()+'@example.test','password':'Only-local-test-password','role':role,'department':'Engineering'}).status_code==200
        u=client();assert u.post('/api/login',json={'email':name.lower()+'@example.test','password':'Only-local-test-password'}).status_code==200;members[role]=u
    finance=members['finance'];member=members['delegate'];head=members['head']
    for key in ['masterProjects','projects','tasks','pos','invoices','updates']:
        assert finance.get('/api/state').json()[key]==[]
    s=c.get('/api/state').json();group=next(g for g in s['departmentGroups'] if g['name']=='Engineering')
    change(c,'project_access',{'id':'erp','accessGroupIds':['unknown']},422)
    change(c,'project_access',{'id':'erp','accessGroupIds':[group['id']]})
    shared=finance.get('/api/state').json();assert [p['id'] for p in shared['projects']]==['erp'];assert shared['pos'] and shared['invoices']
    change(member,'project_access',{'id':'erp','accessGroupIds':[]},403)
    change(member,'update',{'taskId':'erp21','progress':90,'blocked':False,'note':'Unassigned'},403)
    change(finance,'po',{'projectId':'erp','number':'PY-ACCESS','vendor':shared['pos'][0]['vendor'],'amount':100,'date':'2026-09-30','description':'Shared project purchase'})
    change(finance,'payment',{'invoiceId':'inv3','reference':'Hidden ID','paidDate':'2026-09-30'},403)
    s=c.get('/api/state').json();before=s['version'];change(c,'project_access',{'id':'erp','accessGroupIds':[]})
    assert c.post('/api/mutate',json={'version':before,'action':'project_access','payload':{'id':'erp','accessGroupIds':[group['id']]}}).status_code==409
    s=finance.get('/api/state').json();assert not s['projects'] and not s['pos'] and not s['invoices'];assert 'PY-ACCESS' not in json.dumps(s['audit'])
    change(finance,'invoice',{'poId':'po1','number':'Forbidden','amount':1,'date':'2026-09-30','due':'2026-10-30'},403)
    change(head,'project',{'masterId':'bia-digital-transformation','title':'Engineering access test','department':'Engineering','owner':'Lead','budget':100,'start':'2026-09-30','due':'2026-12-31'})
    s=c.get('/api/state').json();p=next(p for p in s['projects'] if p['title']=='Engineering access test');assert p['createdById']==head.get('/api/state').json()['user']['id']
    account=next(u for u in s['users'] if u['name']=='AccessDelegate')
    change(c,'task',{'projectId':p['id'],'title':'Hidden dependency test','resource':'Unassigned','effort':8,'start':'2026-10-30','due':'2026-11-30','predecessors':['erp21'],'assigneeId':account['id']})
    s=head.get('/api/state').json();t=next(t for t in s['tasks'] if t['title']=='Hidden dependency test');assert t['predecessors']==[] and t['externalPredecessorCount']==1 and t['externalPredecessorsPending']==1
    change(head,'task',{**t,'title':'Retained hidden dependency'})
    change(member,'update',{'taskId':t['id'],'progress':10,'blocked':False,'note':'Cannot bypass hidden dependency'},422)
    assert [x['id'] for x in member.get('/api/state').json()['projects']]==[p['id']]
    with engine.connect() as db:
        assert db.execute(select(d.project_groups).where(d.project_groups.c.projectId=='erp')).all()==[]
        assert next(x for x in d.read_state(db)['tasks'] if x['id']==t['id'])['predecessors']==['erp21']

def test_primary_department_validation_persistence_and_rename():
    c=admin()
    def change(action,payload,expected=200):
        s=c.get('/api/state').json();r=c.post('/api/mutate',json={'version':s['version'],'action':action,'payload':payload});assert r.status_code==expected,r.text;return r
    body={'title':'Department validation','owner':'Lead'}
    for department in [None,'','Unknown',123]: change('master',{**body,'primaryDepartment':department},422)
    r=change('master',{**body,'primaryDepartment':'Quality'});master_id=r.json()['masterId']
    s=c.get('/api/state').json();dept=next(x for x in s['catalogs'] if x['kind']=='department' and x['name']=='Quality')
    change('catalog',{**dept,'name':'Quality assurance'})
    s=c.get('/api/state').json();master=next(m for m in s['masterProjects'] if m['id']==master_id);assert master['primaryDepartment']=='Quality assurance'
    change('catalog',{**dept,'name':'Quality assurance','active':False})
    change('master',{**body,'title':'Inactive department','primaryDepartment':'Quality assurance'},422)
    change('master',{**master,'title':'Retained department'})
    change('master',{**master,'primaryDepartment':'Engineering'})
    with engine.connect() as db:
        assert db.execute(select(d.departments.c.name).join(d.masters,d.masters.c.primaryDepartmentId==d.departments.c.id).where(d.masters.c.id==master_id)).scalar_one()=='Engineering'

def test_management_group_reads_all_and_rejects_changes():
    c=admin();password='Management-Python-test-password'
    body={'name':'Python Manager','email':'python-manager@example.test','password':password,'role':'management','department':'Engineering'}
    assert c.post('/api/users',json=body).status_code==200
    manager=client();assert manager.post('/api/login',json={'email':body['email'],'password':password}).status_code==200
    original=c.get('/api/state').json();s=manager.get('/api/state').json()
    for key in ['masterProjects','projects','tasks','pos','invoices','updates']:
        assert {x['id'] for x in s[key]}=={x['id'] for x in original[key]},key
    assert 'password_hash' not in json.dumps(s)
    account=next(u for u in original['users'] if u['email']==body['email']);assert account['id'] in original['managementGroup']['memberIds']
    for action in ['master','project','task','update','po','invoice','payment','catalog','user_edit','project_access']:
        assert manager.post('/api/mutate',json={'action':action,'version':s['version'],'payload':{}}).status_code==403
    assert manager.post('/api/users',json={**body,'email':'forbidden-management@example.test'}).status_code==403
    assert manager.post('/api/users/active',json={'id':'admin','active':False}).status_code==403
    assert manager.post('/api/users/reset-password',json={'id':'admin','password':password,'version':s['version']}).status_code==403
    assert c.post('/api/mutate',json={'action':'user_edit','version':original['version'],'payload':{**account,'role':'executive'}}).status_code==200
    assert manager.get('/api/state').json()['user'] is None
    assert manager.post('/api/login',json={'email':body['email'],'password':password}).status_code==200
    assert manager.get('/api/state').json()['projects']==[]
    s=c.get('/api/state').json();assert c.post('/api/mutate',json={'action':'user_edit','version':s['version'],'payload':account}).status_code==200
    manager.post('/api/login',json={'email':body['email'],'password':password});assert len(manager.get('/api/state').json()['projects'])==len(original['projects'])
    assert c.post('/api/users/active',json={'id':account['id'],'active':False}).status_code==200
    assert manager.get('/api/state').json()['user'] is None
    assert manager.post('/api/login',json={'email':body['email'],'password':password}).status_code==401


def test_lookup_renames_keep_foreign_keys_and_author_links():
    c=admin();before=c.get('/api/state').json()
    def change(action,payload):
        s=c.get('/api/state').json();r=c.post('/api/mutate',json={'action':action,'version':s['version'],'payload':payload});assert r.status_code==200,r.text
    for kind,key,field in [('vendor','pos','vendorId'),('resource','tasks','resourceId')]:
        row=before[key][0];catalog=next(x for x in before['catalogs'] if x['kind']==kind and x['name']==row[kind])
        change('catalog',{**catalog,'name':catalog['name']+' revised'})
        after=c.get('/api/state').json();linked=next(x for x in after[key] if x['id']==row['id'])
        assert linked[field]==row[field] and linked[kind]==catalog['name']+' revised'
    state=c.get('/api/state').json()
    assert any(u['authorId']=='admin' for u in state['updates'])
    assert all('password_hash' not in u for u in state['users'])
    with engine.connect() as db:
        assert 'department' not in db.execute(select(d.users)).mappings().first()
        assert db.execute(select(d.credentials.c.password_hash).where(d.credentials.c.userId=='admin')).scalar_one().startswith('$argon2id$')

def test_request_bounds_password_throttle_and_safe_errors(monkeypatch):
    c=admin()
    assert c.post('/api/login',content='x'*20001,headers={'Content-Type':'application/json'}).status_code==413
    assert c.post('/api/login',json={},headers={'Origin':''}).status_code==403
    # Failed current-password checks persist their counter across transaction rollback.
    for _ in range(8):
        assert c.post('/api/password',json={'current':'wrong-password','password':'Replacement-new-password'}).status_code==422
    assert c.post('/api/password',json={'current':'wrong-password','password':'Replacement-new-password'}).status_code==429
    from sqlalchemy import delete
    from production.app import token_hash
    with engine.begin() as db: db.execute(delete(d.attempts).where(d.attempts.c.key==token_hash('password:admin')))
    def broken(db): raise RuntimeError('secret_connection_details_that_must_not_leak')
    monkeypatch.setattr(d,'read_state',broken)
    response=c.get('/api/state')
    assert response.status_code==500 and 'secret_connection_details' not in response.text and 'reference' in response.text

def test_baselines_immutable_normalized_authorized_and_schedule_revision():
    c=admin()
    def state(): return c.get('/api/state').json()
    def command(action,payload,status=200):
        result=c.post('/api/mutate',json={'action':action,'payload':payload,'version':state()['version']})
        assert result.status_code==status,result.text
        return result
    command('project',dict(masterId='bia-digital-transformation',title='Baseline regression',department='Digital & IT',owner='Lead',budget=100,start='2080-01-01',due='2080-12-31'))
    p=next(p for p in state()['projects'] if p['title']=='Baseline regression')
    command('task',dict(projectId=p['id'],title='Go live',start='2080-02-01',due='2080-02-10',effort=10,resource='Unassigned',predecessors=[],isMilestone=True))
    command('baseline',dict(projectId=p['id'],name='Approved original',reason='Approved plan'))
    s=state();original=next(b for b in s['baselines'] if b['projectId']==p['id']);t=next(t for t in s['tasks'] if t['projectId']==p['id'])
    assert t['isMilestone'] and original['tasks'][0]['isMilestone']
    command('task',{**t,'due':'2080-02-20'},422)
    command('task',{**t,'due':'2080-02-20','changeReason':'Supplier delay'})
    assert next(b for b in state()['baselines'] if b['id']==original['id'])==original
    command('baseline',dict(projectId=p['id'],name='Revised',reason='Revised approval'))
    versions=[b['version'] for b in state()['baselines'] if b['projectId']==p['id']];assert versions==[1,2]
    command('project_dates',dict(projectId=p['id'],start='2080-01-01',due='2081-01-10',reason='Extend schedule'))
    with engine.begin() as db:
        before=d.read_state(db)
        from copy import deepcopy
        changed=deepcopy(before);changed['baselines'][0]['due']='2090-01-01'
        import pytest
        with pytest.raises(RuntimeError,match='immutable'): d.persist_changes(db,before,changed,'admin')
        assert db.execute(select(d.milestones.c.taskId).where(d.milestones.c.taskId==t['id'])).scalar_one()==t['id']
    for role in ['delegate','executive','finance','management','head']:
        email='baseline-'+role+'@example.test'
        assert c.post('/api/users',json=dict(name=role,email=email,password='Only-local-test-password',role=role,department=next(x['name'] for x in state()['catalogs'] if x['kind']=='department' and x['active'] and x['name']!='Digital & IT'))).status_code==200
        viewer=client();assert viewer.post('/api/login',json=dict(email=email,password='Only-local-test-password')).status_code==200
        visible=viewer.get('/api/state').json()
        assert (any(b['projectId']==p['id'] for b in visible['baselines']))==(role=='management')
        assert viewer.post('/api/mutate',json=dict(action='baseline',version=visible['version'],payload=dict(projectId=p['id'],name='Denied',reason='Denied'))).status_code==403

def test_working_calendar_cascade_persistence_and_early_completion():
    c=admin()
    def command(action,payload,status=200):
        version=c.get('/api/state').json()['version']
        r=c.post('/api/mutate',json=dict(action=action,payload=payload,version=version))
        assert r.status_code==status,r.text
        return c.get('/api/state').json()
    s=c.get('/api/state').json();master=s['masterProjects'][0]['id']
    s=command('project',dict(masterId=master,title='Calendar regression',department='Digital & IT',owner='Lead',budget=100,start='2026-01-01',due='2099-12-31',offDays=[5,6]))
    p=next(p for p in s['projects'] if p['title']=='Calendar regression')
    assert p['offDays']==[5,6]
    ids=[]
    for i in range(3):
        s=command('task',dict(projectId=p['id'],title='Calendar '+str(i),resource='Unassigned',effort=8,start=['2099-01-04','2099-01-07','2099-01-11'][i],due=['2099-01-05','2099-01-08','2099-01-12'][i],predecessors=ids[-1:]))
        ids.append(next(t['id'] for t in s['tasks'] if t['title']=='Calendar '+str(i)))
    s=command('project_calendar',dict(projectId=p['id'],offDays=[0,6],reason='Global team'))
    assert next(x for x in s['projects'] if x['id']==p['id'])['offDays']==[0,6]
    original=[t for t in s['tasks'] if t['projectId']==p['id']]
    s=command('baseline',dict(projectId=p['id'],name='Working plan',reason='Approved'))
    first=next(t for t in s['tasks'] if t['id']==ids[0])
    s=command('task',{**first,'due':'2099-01-15','changeReason':'Delayed'})
    from production.scheduling import business
    second=next(t for t in s['tasks'] if t['id']==ids[1]);third=next(t for t in s['tasks'] if t['id']==ids[2])
    assert second['start']==business('2099-01-15',[0,6],True)
    assert third['start']==business(second['due'],[0,6],True)
    s=command('update',dict(taskId=ids[0],progress=100,blocked=False,note='Early completion',rescheduleSuccessors=True))
    from production.domain import today
    assert next(t for t in s['tasks'] if t['id']==ids[1])['start']==business(today(),[0,6],True)
    assert next(b for b in s['baselines'] if b['projectId']==p['id'])['tasks'][0]['due']!= '2099-01-15'
    command('project_calendar',dict(projectId=p['id'],offDays=list(range(7)),reason='Invalid'),422)
