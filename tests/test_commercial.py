import os
os.environ['BIA_TESTING']='1'
from datetime import datetime,timezone
from sqlalchemy import select,insert,delete
from fastapi import HTTPException
import pytest
from production import database as d
from production.domain import mutate
from production.migrations import initialize
from production.access import visible_state

ADMIN=dict(id='admin',name='Admin',role='admin',department='Digital & IT',email='admin@example.test',active=True)
HEAD=dict(id='head',name='Lead',role='head',department='Digital & IT')
@pytest.fixture
def state_engine(tmp_path):
    engine=d.engine_for("sqlite:///"+str(tmp_path/"commercial.db"));initialize(engine)
    with engine.begin() as db:
        d.insert_user(db,{**ADMIN,'password_hash':'not-a-real-login'})
        old=d.read_state(db);catalog=mutate(old,ADMIN,'catalog',dict(kind='vendor',name='External Vendor',active=True));d.persist_changes(db,old,catalog,ADMIN['id']);old=d.read_state(db);vendor=next(c['id'] for c in old['catalogs'] if c['kind']=='vendor')
        new=mutate(old,ADMIN,'project',dict(masterId=old['masterProjects'][0]['id'],title='Currency test',department='Digital & IT',owner='Lead',budget=1000.123,currency='JOD',usdRate=1.41,rateDate='2026-10-01',vendorId=vendor,start='2026-10-01',due='2027-01-01'))
        d.persist_changes(db,old,new,ADMIN['id'])
    yield engine
    engine.dispose()
def change(engine,action,payload):
    with engine.begin() as db:
        old=d.read_state(db);new=mutate(old,ADMIN,action,payload);d.persist_changes(db,old,new,ADMIN['id']);return d.read_state(db)
def test_round_trip_jod_conditions_payment_and_repeated_travel(state_engine):
    engine=state_engine
    with engine.connect() as db:s=d.read_state(db)
    p=s['projects'][0];pid=p['id'];assert p['budget']==1000.123 and p['currency']=='JOD' and p['usdRate']==1.41
    s=change(engine,'payment_term',dict(projectId=pid,title='Deposit',trigger='date',dueDate='2026-10-02',amount=100.123,cancelled=False));term=s['paymentTerms'][0]
    vendor=next(c['name'] for c in s['catalogs'] if c['id']==p['vendorId'])
    s=change(engine,'po',dict(projectId=pid,number='PO1',vendor=vendor,amount=200.123,date='2026-10-01',description='Services'));po=s['pos'][0]
    s=change(engine,'invoice',dict(poId=po['id'],number='INV1',amount=100.123,date='2026-10-01',due='2026-10-02',termId=term['id']));inv=s['invoices'][0];assert inv['termId']==term['id'] and inv['amount']==100.123
    s=change(engine,'payment',dict(invoiceId=inv['id'],reference='BANK-1',paidDate='2026-10-02'));assert s['invoices'][0]['status']=='Paid'
    s=change(engine,'consultant',dict(projectId=pid,vendorId=p['vendorId'],name='Consultant One',active=True));c=s['consultants'][0]
    trip=dict(projectId=pid,consultantId=c['id'],start='2026-10-20',end='2026-10-23',biaFlight=True,biaAccommodation=True,biaFood=True,stayType='campus',flightBooked=True,bookedDate='2026-10-02',flightCost=75.123,notes='Visit one')
    s=change(engine,'trip',trip);s=change(engine,'trip',{**trip,'start':'2026-11-20','end':'2026-11-22','stayType':'external'})
    assert len(s['trips'])==2 and all(t['flightCost']==75.123 for t in s['trips'])
    hidden=visible_state(s,dict(id='outsider',role='head',department='HR'));assert hidden['trips']==[] and hidden['consultants']==[] and hidden['paymentTerms']==[]
    with pytest.raises(HTTPException):mutate(s,ADMIN,'project_commercial',{**p,'projectId':pid,'currency':'EUR','usdRate':1.1})
    with pytest.raises(HTTPException):mutate(s,HEAD,'trip',{**trip,'flightCost':-1})
    with pytest.raises(HTTPException):mutate(s,{**ADMIN,'role':'management'},'trip',trip)
    with pytest.raises(HTTPException):mutate(s,HEAD,'consultant',dict(projectId=pid,id=c['id'],name='Changed shared',active=True))
def test_currency_precision_and_milestone_integrity(state_engine):
    engine=state_engine
    with engine.connect() as db:s=d.read_state(db)
    p=s['projects'][0]
    for b in [dict(currency='INVALID'),dict(budget=1.2345),dict(usdRate=0),dict(rateDate='2999-01-01')]:
        with pytest.raises(HTTPException):mutate(s,ADMIN,'project_commercial',{**p,'projectId':p['id'],**b})
    s=change(engine,'task',dict(projectId=p['id'],title='Milestone',isMilestone=True,start='2026-10-01',due='2026-10-02',effort=1,resource='Unassigned'));task=s['tasks'][0]
    s=change(engine,'payment_term',dict(projectId=p['id'],title='On acceptance',trigger='milestone',milestoneId=task['id'],amount=100,cancelled=False))
    assert s['paymentTerms'][0]['milestoneId']==task['id']
    with pytest.raises(HTTPException):mutate(s,ADMIN,'task',{**task,'isMilestone':False})
def test_v9_upgrade_is_repeatable_and_preserves_legacy_usd(state_engine):
    engine=state_engine
    with engine.begin() as db:
        # Simulate v9: no commercial extension tables, original project amount.
        for table in reversed(d.metadata.sorted_tables):
            if table in d.COMMERCIAL_TABLES+d.EXPENSE_TABLES:table.drop(db)
        db.execute(delete(d.schema_migrations));db.execute(insert(d.schema_migrations).values(version=9,appliedAt=datetime.now(timezone.utc)))
        project=list(db.execute(select(d.projects)).mappings())[0]
    initialize(engine);initialize(engine)
    with engine.connect() as db:
        s=d.read_state(db);p=s['projects'][0]
        assert p['id']==project['id'] and p['budget']==float(project['budget']) and p['currency']=='USD' and p['usdRate']==1
        assert s['paymentTerms']==[] and s['trips']==[]
        assert set(db.execute(select(d.schema_migrations.c.version)).scalars())=={9,12}

def test_designations_jod_expenses_and_v10_migration(state_engine):
    engine=state_engine
    with engine.connect() as db:s=d.read_state(db)
    p=s['projects'][0];pid=p['id']
    # Additive migration leaves existing commercial data untouched.
    with engine.begin() as db:
        for table in reversed(d.EXPENSE_TABLES): table.drop(db)
        db.execute(delete(d.schema_migrations));db.execute(insert(d.schema_migrations).values(version=10,appliedAt=datetime.now(timezone.utc)))
    initialize(engine);initialize(engine)
    s=change(engine,'project_commercial',{**p,'projectId':pid,'vendorId':None})
    with pytest.raises(HTTPException):mutate(s,HEAD,'consultant',dict(projectId=pid,vendorId=p['vendorId'],name='Architect',designation='Solution architect',active=True))
    s=change(engine,'consultant',dict(projectId=pid,vendorId=p['vendorId'],name='Architect',designation='Solution architect',active=True,assignProjectVendor=True))
    assert s['projects'][0]['vendorId']==p['vendorId'] and s['consultants'][0]['designation']=='Solution architect'
    trip=dict(projectId=pid,consultantId=s['consultants'][0]['id'],start='2026-10-20',end='2026-10-23',biaFlight=True,biaAccommodation=True,stayType='external',flightBooked=True,bookedDate='2026-10-02',flightCostJod=75.123,hotelBookedBy='bia',hotelCostJod=200,visaCostJod=30,notes='Visit')
    s=change(engine,'trip',trip);assert s['trips'][0]['flightCostJod']==75.123 and s['trips'][0]['hotelCostJod']==200
    s=change(engine,'trip',{**trip,'id':s['trips'][0]['id'],'hotelBookedBy':'vendor'});assert s['trips'][0]['hotelCostJod']==0
    b=dict(projectId=pid,kind='spares',date='2026-10-02',prNumber='PR1',amountJod=123.456,remarks='Replacement drive')
    s=change(engine,'expense',b);assert s['expenses'][0]['amountJod']==123.456
    with pytest.raises(HTTPException):mutate(s,ADMIN,'expense',b)
    with pytest.raises(HTTPException):mutate(s,ADMIN,'expense',{**b,'prNumber':'PR2','amountJod':1.1234})
    outside=dict(id='out',role='head',department='HR')
    assert visible_state(s,outside)['expenses']==[]
    with pytest.raises(HTTPException):mutate(s,outside,'expense',{**b,'prNumber':'PR3'})
    with engine.connect() as db: assert set(db.execute(select(d.schema_migrations.c.version)).scalars())=={10,12}

def test_v11_upgrade_budget_approval_invoice_link_and_atomicity(state_engine):
    engine=state_engine
    with engine.begin() as db:
        for table in reversed(d.CHANGE_TABLES):table.drop(db)
        db.execute(delete(d.schema_migrations));db.execute(insert(d.schema_migrations).values(version=11,appliedAt=datetime.now(timezone.utc)))
        reviewer={**ADMIN,'id':'reviewer','name':'Reviewer','email':'reviewer@example.test'}
        d.insert_user(db,{**reviewer,'password_hash':'not-a-login'})
    initialize(engine);initialize(engine)
    with engine.connect() as db:s=d.read_state(db)
    p=s['projects'][0];pid=p['id'];before=p['budget']
    s=change(engine,'change_request',dict(projectId=pid,title='Additional integration',reason='New external interface',amount=25.123));cr=s['changeRequests'][0]
    assert s['projects'][0]['budget']==before
    decision=dict(projectId=pid,id=cr['id'],decision='Approved',decisionNote='Reviewed and approved')
    with pytest.raises(HTTPException):mutate(s,ADMIN,'change_decision',decision)
    with engine.begin() as db:
        old=d.read_state(db);new=mutate(old,reviewer,'change_decision',decision);d.persist_changes(db,old,new,reviewer['id'])
    with engine.connect() as db:s=d.read_state(db)
    assert s['projects'][0]['budget']==1025.246
    assert s['changeRequests'][0]['budgetBefore']==before and s['changeRequests'][0]['budgetAfter']==1025.246
    with pytest.raises(HTTPException):mutate(s,reviewer,'change_decision',decision)
    with pytest.raises(HTTPException):mutate(s,ADMIN,'project_commercial',{**p,'projectId':pid,'budget':2000})
    vendor=next(c['name'] for c in s['catalogs'] if c['id']==p['vendorId'])
    s=change(engine,'po',dict(projectId=pid,number='CR-PO',vendor=vendor,amount=100,date='2026-10-01',description='Additional work'))
    b=dict(poId=s['pos'][0]['id'],number='CR-INV',amount=25.123,date='2026-10-02',due='2026-10-03',changeRequestId=cr['id'])
    s=change(engine,'invoice',b);assert s['invoices'][0]['changeRequestId']==cr['id']
    assert s['projects'][0]['budget']==1025.246
    with pytest.raises(HTTPException):change(engine,'invoice',{**b,'number':'CR-INV-EXCESS','amount':1})
    with engine.connect() as db:
        assert len(d.read_state(db)['invoices'])==1
        assert set(db.execute(select(d.schema_migrations.c.version)).scalars())=={11,12}
    s=change(engine,'change_request',dict(projectId=pid,title='Rejected scope',reason='Alternative',amount=10));pending=next(c for c in s['changeRequests'] if c['status']=='Pending')
    with engine.begin() as db:
        old=d.read_state(db);new=mutate(old,reviewer,'change_decision',dict(projectId=pid,id=pending['id'],decision='Rejected',decisionNote='Not required'));d.persist_changes(db,old,new,reviewer['id'])
    with engine.connect() as db:
        final=d.read_state(db);assert final['projects'][0]['budget']==1025.246
        assert next(c for c in final['changeRequests'] if c['id']==pending['id'])['status']=='Rejected'

def test_finance_central_inbox_is_minimal_and_keeps_project_scope(state_engine):
    engine=state_engine
    with engine.connect() as db:s=d.read_state(db)
    p=s['projects'][0];s=mutate(s,ADMIN,'change_request',dict(projectId=p['id'],title='Extra',reason='New scope',amount=10));c=s['changeRequests'][0]
    finance=dict(id='central',name='Central finance',role='finance',department='HR')
    view=visible_state(s,finance)
    assert view['projects']==[] and view['tasks']==[] and view['invoices']==[]
    assert set(view['approvalInbox'][0]['project'])=={'id','title','department','currency','budget'}
    approved=mutate(s,finance,'change_decision',dict(projectId=p['id'],id=c['id'],decision='Approved',decisionNote='Reviewed'))
    assert approved['projects'][0]['budget']==1010.123
    with pytest.raises(HTTPException):mutate(s,finance,'project_commercial',{**p,'projectId':p['id']})
    assert visible_state(s,{**finance,'role':'delegate'})['approvalInbox']==[]


def test_commercial_commands_through_authenticated_http(state_engine, monkeypatch):
    # Exercise request validation, authorization, transaction and persistence together.
    # Calling domain.mutate alone cannot catch a stale FastAPI action allowlist.
    os.environ.setdefault('DATABASE_URL', 'sqlite://')
    os.environ.setdefault('TRUSTED_ORIGINS', 'http://testserver')
    from fastapi.testclient import TestClient
    from sqlalchemy import update
    from production import app as api
    monkeypatch.setattr(api, 'engine', state_engine)
    password = 'Local-api-regression-password'
    with state_engine.begin() as db:
        db.execute(update(d.credentials).where(d.credentials.c.userId=='admin').values(password_hash=api.ph.hash(password)))
    headers={'Origin':'http://testserver','X-BIA-Request':'1'}
    c=TestClient(api.app,headers=headers)
    assert c.post('/api/login',json={'email':ADMIN['email'],'password':password}).status_code==200
    assert c.get('/api/health').json()=={'status':'ok','schemaVersion':12,'apiRelease':'2026-10-18.1'}
    def state(who=c): return who.get('/api/state').json()
    def command(action,payload,who=c,expected=200):
        before=state(who)
        r=who.post('/api/mutate',json=dict(action=action,payload=payload,version=before['version']))
        assert r.status_code==expected,r.text
        if expected!=200: assert state(c)['version']==before['version']
        return state(who)
    p=state()['projects'][0];pid=p['id']
    s=command('project_commercial',{**p,'projectId':pid,'usdRate':1.4})
    assert s['projects'][0]['usdRate']==1.4
    s=command('payment_term',dict(projectId=pid,title='Deposit',trigger='date',dueDate='2026-10-02',amount=25.123,cancelled=False))
    term=s['paymentTerms'][0]
    s=command('payment_term',{**term,'title':'Updated deposit'})
    assert s['paymentTerms'][0]['title']=='Updated deposit'
    s=command('consultant',dict(projectId=pid,vendorId=p['vendorId'],name='HTTP Consultant',designation='Architect',active=True))
    consultant=s['consultants'][0]
    s=command('consultant',{**consultant,'projectId':pid,'designation':'Lead architect'})
    assert s['consultants'][0]['designation']=='Lead architect'
    trip=dict(projectId=pid,consultantId=consultant['id'],start='2026-10-20',end='2026-10-23',biaFlight=True,biaAccommodation=True,stayType='external',flightBooked=True,bookedDate='2026-10-02',flightCostJod=75.123,hotelBookedBy='bia',hotelCostJod=200,visaCostJod=30,notes='API visit')
    s=command('trip',trip)
    s=command('trip',{**trip,'id':s['trips'][0]['id'],'hotelCostJod':210.123})
    assert s['trips'][0]['hotelCostJod']==210.123
    expense=dict(projectId=pid,kind='spares',date='2026-10-02',prNumber='HTTP-PR',amountJod=123.456,remarks='Spare')
    s=command('expense',expense)
    s=command('expense',{**expense,'id':s['expenses'][0]['id'],'amountJod':124.456})
    assert s['expenses'][0]['amountJod']==124.456
    command('expense',{**expense,'prNumber':'INVALID','amountJod':-1},expected=422)
    command('unknown_action',{},expected=422)
    assert c.post('/api/users',json=dict(name='Finance reviewer',email='reviewer@example.test',password=password,role='finance',department='HR',version=state()['version'])).status_code==200
    reviewer=TestClient(api.app,headers=headers)
    assert reviewer.post('/api/login',json=dict(email='reviewer@example.test',password=password)).status_code==200
    s=command('change_request',dict(projectId=pid,title='HTTP budget',reason='Additional interface',amount=25.123))
    cr=s['changeRequests'][0];decision=dict(projectId=pid,id=cr['id'],decision='Approved',decisionNote='Reviewed')
    command('change_decision',decision,expected=422)  # no self approval
    assert state(reviewer)['projects']==[]
    assert state(reviewer)['approvalInbox'][0]['request']['id']==cr['id']
    command('change_decision',decision,who=reviewer)
    command('change_decision',decision,who=reviewer,expected=422)  # no replay
    s=state();assert s['projects'][0]['budget']==1025.246
    vendor=next(x['name'] for x in s['catalogs'] if x['id']==p['vendorId'])
    s=command('po',dict(projectId=pid,number='HTTP-PO',vendor=vendor,amount=100,date='2026-10-01',description='Services'))
    s=command('invoice',dict(poId=s['pos'][0]['id'],number='HTTP-INV',amount=25.123,date='2026-10-01',due='2026-10-02',termId=term['id'],changeRequestId=cr['id']))
    inv=s['invoices'][0]
    assert inv['changeRequestId']==cr['id'] and inv['termId']==term['id']
    s=command('payment',dict(invoiceId=inv['id'],reference='BANK-HTTP',paidDate='2026-10-02'))
    assert s['invoices'][0]['status']=='Paid' and s['projects'][0]['budget']==1025.246
    assert c.post('/api/logout',json={}).status_code==200
    assert c.get('/api/state').json()['user'] is None


def test_http_command_contract_covers_domain_handlers():
    import ast
    from pathlib import Path
    from typing import get_args
    from production.app import Command
    from production.commercial import ACTIONS
    tree=ast.parse(Path('production/domain.py').read_text())
    core=set()
    for node in ast.walk(tree):
        if isinstance(node,ast.Compare) and isinstance(node.left,ast.Name) and node.left.id=='action':
            for other in node.comparators:
                if isinstance(other,ast.Constant) and isinstance(other.value,str): core.add(other.value)
    assert set(get_args(Command.model_fields['action'].annotation))==core|set(ACTIONS)
