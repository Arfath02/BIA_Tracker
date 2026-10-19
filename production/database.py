"""Normalized v12 SQL Server tables and the API's relational storage adapter.

All application tables live in the bia schema. The UI receives joined display
names; relationships are stored as IDs. No business records are JSON blobs.
"""
import os
from datetime import date, datetime, timezone
from decimal import Decimal
from sqlalchemy import (MetaData, Table, Column as C, String as S, Unicode as U,
    Integer as I, Numeric as N, Boolean as B, ForeignKey as FK,
    ForeignKeyConstraint as FKC, CheckConstraint as CK, UniqueConstraint as UK,
    Date, DateTime, TypeDecorator, Index, create_engine, select, insert, update,
    delete, event)
from sqlalchemy.dialects import mssql
from sqlalchemy.engine import make_url

SCHEMA_VERSION = 12
metadata = MetaData(schema='bia', naming_convention={
    'pk':'pk_%(table_name)s', 'fk':'fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s',
    'uq':'uq_%(table_name)s_%(column_0_name)s', 'ix':'ix_%(table_name)s_%(column_0_name)s',
    'ck':'ck_%(table_name)s_%(constraint_name)s'})

class ISODate(TypeDecorator):
    impl = Date
    cache_ok = True
    def load_dialect_impl(self, dialect):
        return mssql.DATE() if dialect.name == 'mssql' else Date()
    def process_bind_param(self, value, dialect):
        return date.fromisoformat(value) if isinstance(value, str) else value
    def process_result_value(self, value, dialect):
        return value.isoformat() if value else None

class UTCDateTime(TypeDecorator):
    impl = DateTime
    cache_ok = True
    def load_dialect_impl(self, dialect):
        return dialect.type_descriptor(mssql.DATETIME2(precision=6) if dialect.name == 'mssql' else DateTime())
    def process_bind_param(self, value, dialect):
        if isinstance(value, str): value = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if value is not None:
            if value.tzinfo is None: value = value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc).replace(tzinfo=None)
    def process_result_value(self, value, dialect):
        return value.replace(tzinfo=timezone.utc).isoformat() if value else None

def label_type(length):
    return U(length).with_variant(mssql.NVARCHAR(length, collation='Latin1_General_100_CI_AS_SC'), 'mssql')

def lookup(name, length):
    return Table(name, metadata, C('id', S(36), primary_key=True),
        C('name', label_type(length), nullable=False, unique=True), C('active', B, nullable=False),
        CK("LEN(name)>0", name='name_required').ddl_if(dialect='mssql'))

schema_migrations = Table('schema_migrations', metadata, C('version', I, primary_key=True, autoincrement=False), C('appliedAt', UTCDateTime(), nullable=False))
workspace = Table('workspace', metadata, C('id', I, primary_key=True, autoincrement=False), C('version', I, nullable=False), CK('id=1', name='singleton'), CK('version>=1', name='version_positive'))
roles = Table('roles', metadata, C('code', S(20), primary_key=True), C('name', U(80), nullable=False), CK("code IN ('admin','head','delegate','finance','executive','management')", name='known_role'))
departments = lookup('departments', 60)
vendors = lookup('vendors', 100)
resources = lookup('resources', 80)
users = Table('users', metadata, C('id', S(36), primary_key=True), C('email', label_type(254), unique=True, nullable=False), C('name', U(80), nullable=False), C('role', S(20), FK('bia.roles.code'), nullable=False), C('departmentId', S(36), FK('bia.departments.id'), nullable=False, index=True), C('active', B, nullable=False))
credentials = Table('user_credentials', metadata, C('userId', S(36), FK('bia.users.id'), primary_key=True), C('password_hash', S(255), nullable=False))
masters = Table('master_projects', metadata, C('id', S(36), primary_key=True), C('title', label_type(100), nullable=False, unique=True), C('primaryDepartmentId', S(36), FK('bia.departments.id'), index=True), C('owner', U(80), nullable=False), C('description', U(1000)))
projects = Table('projects', metadata, C('id', S(36), primary_key=True), C('masterId', S(36), FK('bia.master_projects.id'), nullable=False, index=True), C('createdById', S(36), FK('bia.users.id'), index=True), C('title', U(100), nullable=False), C('departmentId', S(36), FK('bia.departments.id'), nullable=False, index=True), C('owner', U(80), nullable=False), C('budget', N(19,4), nullable=False), C('start', ISODate(), nullable=False), C('due', ISODate(), nullable=False), C('description', U(1000)), C('color', S(10)), CK('budget>=0', name='budget_nonnegative'), CK('due>=start', name='dates_ordered'))
tasks = Table('tasks', metadata, C('id', S(36), primary_key=True), C('projectId', S(36), FK('bia.projects.id'), nullable=False, index=True), C('parentId', S(36)), C('title', U(180), nullable=False), C('assigneeId', S(36), FK('bia.users.id'), index=True), C('resourceId', S(36), FK('bia.resources.id'), nullable=False, index=True), C('effort', N(12,2), nullable=False), C('start', ISODate(), nullable=False), C('due', ISODate(), nullable=False), C('progress', I, nullable=False), C('blocked', B, nullable=False), UK('id','projectId'), FKC(['parentId','projectId'], ['bia.tasks.id','bia.tasks.projectId'], name='fk_tasks_parent_same_project'), CK('parentId IS NULL OR parentId<>id', name='not_own_parent'), CK('progress>=0 AND progress<=100', name='progress_range'), CK('effort>0', name='effort_positive'), CK('due>=start', name='dates_ordered'), CK('progress<100 OR blocked=0', name='complete_not_blocked'))
Index('ix_tasks_parent_project', tasks.c.parentId, tasks.c.projectId)
predecessors = Table('task_predecessors', metadata, C('taskId', S(36), FK('bia.tasks.id'), primary_key=True), C('predecessorId', S(36), FK('bia.tasks.id'), primary_key=True, index=True), CK('taskId<>predecessorId', name='not_self'))
project_groups = Table('project_department_access', metadata, C('projectId', S(36), FK('bia.projects.id'), primary_key=True), C('groupId', S(36), FK('bia.departments.id'), primary_key=True, index=True))
pos = Table('purchase_orders', metadata, C('id', S(36), primary_key=True), C('projectId', S(36), FK('bia.projects.id'), nullable=False, index=True), C('number', label_type(60), unique=True, nullable=False), C('vendorId', S(36), FK('bia.vendors.id'), nullable=False, index=True), C('amount', N(19,4), nullable=False), C('date', ISODate(), nullable=False), C('description', U(300), nullable=False), CK('amount>0', name='amount_positive'))
invoices = Table('invoices', metadata, C('id', S(36), primary_key=True), C('poId', S(36), FK('bia.purchase_orders.id'), nullable=False, index=True), C('number', label_type(60), nullable=False), C('amount', N(19,4), nullable=False), C('date', ISODate(), nullable=False), C('due', ISODate(), nullable=False), CK('amount>0', name='amount_positive'), CK('due>=date', name='dates_ordered'), UK('poId','number'))
# Current business workflow is one full settlement per invoice, not partial payments.
payments = Table('invoice_payments', metadata, C('invoiceId', S(36), FK('bia.invoices.id'), primary_key=True), C('reference', U(100), nullable=False), C('paidDate', ISODate(), nullable=False), C('recordedById', S(36), FK('bia.users.id'), index=True))
updates = Table('progress_updates', metadata, C('id', S(36), primary_key=True), C('taskId', S(36), FK('bia.tasks.id'), nullable=False, index=True), C('progress', I, nullable=False), C('note', U(2000), nullable=False), C('authorId', S(36), FK('bia.users.id'), index=True), C('author', U(80), nullable=False), C('createdAt', UTCDateTime(), nullable=False, index=True), CK('progress>=0 AND progress<=100', name='progress_range'))
audit = Table('audit_log', metadata, C('id', S(36), primary_key=True), C('projectId', S(36), FK('bia.projects.id'), index=True), C('actorId', S(36), FK('bia.users.id'), index=True), C('actor', U(80), nullable=False), C('role', S(20), nullable=False), C('action', U(500), nullable=False), C('at', UTCDateTime(), nullable=False, index=True))
sessions = Table('sessions', metadata, C('token', S(64), primary_key=True), C('user_id', S(36), FK('bia.users.id'), nullable=False, index=True), C('expires', N(18,0), nullable=False, index=True))
attempts = Table('login_attempts', metadata, C('key', S(64), primary_key=True), C('count', I, nullable=False), C('expires', N(18,0), nullable=False, index=True), CK('count>=1', name='count_positive'))
project_days_off = Table('project_days_off', metadata, C('projectId', S(36), FK('bia.projects.id'), primary_key=True), C('weekday', I, primary_key=True), CK('weekday>=0 AND weekday<=6', name='weekday_valid'))
milestones = Table('task_milestones', metadata, C('taskId', S(36), FK('bia.tasks.id'), primary_key=True))
baselines = Table('project_baselines', metadata, C('id', S(36), primary_key=True), C('projectId', S(36), FK('bia.projects.id'), nullable=False, index=True), C('version', I, nullable=False), C('name', U(80), nullable=False), C('reason', U(500), nullable=False), C('createdById', S(36), FK('bia.users.id'), nullable=False, index=True), C('createdBy', U(80), nullable=False), C('createdAt', UTCDateTime(), nullable=False), C('title', U(100), nullable=False), C('start', ISODate(), nullable=False), C('due', ISODate(), nullable=False), UK('projectId','version'), CK('version>=1', name='version_positive'), CK('due>=start', name='dates_ordered'))
baseline_tasks = Table('baseline_tasks', metadata, C('baselineId', S(36), FK('bia.project_baselines.id'), primary_key=True), C('taskId', S(36), FK('bia.tasks.id'), primary_key=True, index=True), C('parentId', S(36), FK('bia.tasks.id'), index=True), C('title', U(180), nullable=False), C('start', ISODate(), nullable=False), C('due', ISODate(), nullable=False), C('effort', N(12,2), nullable=False), C('isMilestone', B, nullable=False), CK('effort>0', name='effort_positive'), CK('due>=start', name='dates_ordered'))
# Financial settings extend existing project records without reinterpreting legacy USD.
currency_codes = Table('currency_codes', metadata, C('code', S(3), primary_key=True), C('name', U(100), nullable=False), C('digits', I, nullable=False), CK('digits>=0 AND digits<=4', name='digits_range'))
project_finance = Table('project_finance', metadata, C('projectId', S(36), FK('bia.projects.id'), primary_key=True), C('currency', S(3), FK('bia.currency_codes.code'), nullable=False), C('usdRate', N(18,8), nullable=False), C('rateDate', ISODate()), C('vendorId', S(36), FK('bia.vendors.id'), index=True), CK('usdRate>0', name='rate_positive'), CK("currency<>'USD' OR usdRate=1", name='usd_rate_one'))
payment_terms = Table('payment_terms', metadata, C('id', S(36), primary_key=True), C('projectId', S(36), FK('bia.projects.id'), nullable=False, index=True), C('title', U(100), nullable=False), C('amount', N(19,4), nullable=False), C('trigger', S(20), nullable=False), C('dueDate', ISODate()), C('milestoneId', S(36)), C('cancelled', B, nullable=False), FKC(['milestoneId','projectId'],['bia.tasks.id','bia.tasks.projectId'],name='fk_terms_milestone_project'), CK('amount>0', name='amount_positive'), CK("([trigger]='date' AND dueDate IS NOT NULL AND milestoneId IS NULL) OR ([trigger]='milestone' AND dueDate IS NULL AND milestoneId IS NOT NULL)", name='valid_trigger'))
invoice_terms = Table('invoice_terms', metadata, C('invoiceId', S(36), FK('bia.invoices.id'), primary_key=True), C('termId', S(36), FK('bia.payment_terms.id'), nullable=False, unique=True))
consultants = Table('vendor_consultants', metadata, C('id', S(36), primary_key=True), C('vendorId', S(36), FK('bia.vendors.id'), nullable=False, index=True), C('ownerProjectId', S(36), FK('bia.projects.id'), index=True), C('name', label_type(100), nullable=False), C('active', B, nullable=False), UK('vendorId','name'))
trips = Table('consultant_trips', metadata, C('id', S(36), primary_key=True), C('projectId', S(36), FK('bia.projects.id'), nullable=False, index=True), C('consultantId', S(36), FK('bia.vendor_consultants.id'), nullable=False, index=True), C('start', ISODate(), nullable=False), C('end', ISODate(), nullable=False), C('biaFlight', B, nullable=False), C('biaAccommodation', B, nullable=False), C('biaFood', B, nullable=False), C('stayType', S(20)), C('flightBooked', B, nullable=False), C('flightCost', N(19,4)), C('bookedDate', ISODate()), C('notes', U(1000), nullable=False), CK('[end]>=start', name='dates_ordered'), CK("(biaAccommodation=0 AND stayType IS NULL) OR (biaAccommodation=1 AND stayType IN ('campus','external'))", name='stay_valid'), CK('(flightBooked=0 AND flightCost IS NULL AND bookedDate IS NULL) OR (flightBooked=1 AND biaFlight=1 AND flightCost>0 AND bookedDate IS NOT NULL AND bookedDate<=start)', name='flight_valid'))
consultant_details = Table('consultant_details', metadata, C('consultantId', S(36), FK('bia.vendor_consultants.id'), primary_key=True), C('designation', U(100), nullable=False))
trip_costs = Table('trip_costs', metadata, C('tripId', S(36), FK('bia.consultant_trips.id'), primary_key=True), C('flightCostJod', N(19,3)), C('hotelBookedBy', S(10)), C('hotelCostJod', N(19,3), nullable=False), C('visaCostJod', N(19,3), nullable=False), CK('flightCostJod IS NULL OR flightCostJod>0',name='flight_positive'), CK('hotelCostJod>=0 AND visaCostJod>=0',name='costs_nonnegative'), CK("hotelBookedBy IS NULL OR hotelBookedBy IN ('bia','vendor')",name='booker_valid'), CK("hotelCostJod=0 OR hotelBookedBy='bia'",name='bia_hotel_only'))
expenses = Table('project_expenses', metadata, C('id', S(36), primary_key=True), C('projectId', S(36), FK('bia.projects.id'), nullable=False, index=True), C('kind', S(20), nullable=False), C('date', ISODate(), nullable=False), C('prNumber', label_type(60), nullable=False), C('amountJod', N(19,3), nullable=False), C('remarks', U(1000), nullable=False), CK("kind IN ('spares','miscellaneous')",name='kind_valid'), CK('amountJod>0',name='amount_positive'), UK('projectId','kind','prNumber'))
change_requests=Table('budget_change_requests', metadata, C('id', S(36), primary_key=True), C('projectId', S(36), FK('bia.projects.id'), nullable=False,index=True), C('title', U(100),nullable=False), C('reason', U(2000),nullable=False), C('amount',N(19,4),nullable=False), C('status',S(10),nullable=False), C('requestedById',S(36),FK('bia.users.id'),nullable=False), C('requestedBy',U(100),nullable=False), C('requestedDate',ISODate(),nullable=False), C('decidedById',S(36),FK('bia.users.id')), C('decidedBy',U(100)), C('decisionDate',ISODate()), C('decisionNote',U(2000)), C('budgetBefore',N(19,4)), C('budgetAfter',N(19,4)), CK('amount>0',name='amount_positive'), CK("status IN ('Pending','Approved','Rejected')",name='status_valid'), CK("(status='Pending' AND decidedById IS NULL AND decisionDate IS NULL AND decisionNote IS NULL AND budgetBefore IS NULL AND budgetAfter IS NULL) OR (status IN ('Approved','Rejected') AND decidedById IS NOT NULL AND decidedById<>requestedById AND decisionDate IS NOT NULL AND decisionDate>=requestedDate AND decisionNote IS NOT NULL)",name='review_valid'), CK("(status='Approved' AND budgetBefore IS NOT NULL AND budgetAfter IS NOT NULL AND budgetBefore>=0 AND budgetAfter=budgetBefore+amount) OR (status<>'Approved' AND budgetBefore IS NULL AND budgetAfter IS NULL)",name='budget_valid'))
invoice_changes=Table('invoice_budget_changes',metadata,C('invoiceId',S(36),FK('bia.invoices.id'),primary_key=True),C('changeRequestId',S(36),FK('bia.budget_change_requests.id'),nullable=False,index=True))
CHANGE_TABLES=[change_requests,invoice_changes]
EXPENSE_TABLES=[consultant_details,trip_costs,expenses]
COMMERCIAL_TABLES=[currency_codes,project_finance,payment_terms,invoice_terms,consultants,trips]
LOOKUPS = {'department':departments, 'vendor':vendors, 'resource':resources}
TABLES = {'masterProjects':masters, 'projects':projects, 'tasks':tasks, 'pos':pos, 'invoices':invoices, 'updates':updates, 'audit':audit,'paymentTerms':payment_terms,'consultants':consultants,'trips':trips,'expenses':expenses,'changeRequests':change_requests}
ROLE_ROWS = [{'code':code, 'name':name} for code,name in [('admin','Administrator'),('head','Vertical head'),('delegate','Delegate'),('finance','Finance'),('executive','Executive (scoped)'),('management','Management (read-only)')]]

def engine_for(url):
    if not url: raise RuntimeError('DATABASE_URL must be configured.')
    parsed = make_url(url)
    testing = os.getenv('BIA_TESTING') == '1'
    if parsed.drivername != 'mssql+pyodbc' and not testing: raise RuntimeError('Production requires Microsoft SQL Server through pyodbc.')
    if not testing:
        query = {k.lower():str(v).lower() for k,v in parsed.query.items()}
        if query.get('driver') != 'odbc driver 18 for sql server' or query.get('encrypt') not in ('yes','true','mandatory','strict') or query.get('trustservercertificate') not in ('no','false') or 'odbc_connect' in query:
            raise RuntimeError('Use ODBC Driver 18, Encrypt=yes and TrustServerCertificate=no; raw ODBC overrides are not accepted.')
    kwargs = {'pool_pre_ping':True, 'hide_parameters':True}
    if parsed.drivername.startswith('sqlite'):
        kwargs.update(connect_args={'check_same_thread':False}, execution_options={'schema_translate_map':{'bia':None}})
    result = create_engine(url, **kwargs)
    if parsed.drivername.startswith('sqlite'):
        @event.listens_for(result, 'connect')
        def enable_fks(connection, record): connection.execute('PRAGMA foreign_keys=ON')
    return result

def asdict(row):
    return {k:float(v) if isinstance(v,Decimal) else v for k,v in dict(row).items()}

def user_select():
    return select(*users.c, departments.c.name.label('department')).join(departments, users.c.departmentId==departments.c.id)

def read_state(db):
    result = {key:[asdict(r) for r in db.execute(select(table)).mappings()] for key,table in TABLES.items()}
    result['catalogs'] = [{**dict(r),'kind':kind} for kind,table in LOOKUPS.items() for r in db.execute(select(table)).mappings()]
    names = {r['id']:r['name'] for r in result['catalogs']}
    result['users'] = [dict(r) for r in db.execute(user_select()).mappings()]
    for row in result['masterProjects']: row['primaryDepartment'] = names.get(row['primaryDepartmentId'])
    designations={r['consultantId']:r['designation'] for r in db.execute(select(consultant_details)).mappings()}
    for row in result['consultants']: row['designation']=designations.get(row['id'],'')
    costs={r['tripId']:asdict(r) for r in db.execute(select(trip_costs)).mappings()}
    for row in result['trips']:
        if row['id'] in costs: row.update({k:v for k,v in costs[row['id']].items() if k!='tripId'})
    profiles={r['projectId']:asdict(r) for r in db.execute(select(project_finance)).mappings()}
    for row in result['projects']:
        row['department'] = names[row['departmentId']]
        row.update({k:v for k,v in profiles.get(row['id'],dict(currency='USD',usdRate=1,rateDate=None,vendorId=None)).items() if k!='projectId'})
    days=list(db.execute(select(project_days_off)).mappings())
    for p in result['projects']: p['offDays']=sorted(r['weekday'] for r in days if r['projectId']==p['id'])
    project_depts = {row['id']:row['department'] for row in result['projects']}
    for row in result['tasks']:
        row['resource'] = names[row['resourceId']]
        row['department'] = project_depts[row['projectId']]
    for row in result['pos']: row['vendor'] = names[row['vendorId']]
    change_links={r['invoiceId']:r['changeRequestId'] for r in db.execute(select(invoice_changes)).mappings()}
    term_links={r['invoiceId']:r['termId'] for r in db.execute(select(invoice_terms)).mappings()}
    paid = {r['invoiceId']:dict(r) for r in db.execute(select(payments)).mappings()}
    for row in result['invoices']:
        payment = paid.get(row['id']);row['termId']=term_links.get(row['id']);row['changeRequestId']=change_links.get(row['id'])
        row.update(status='Paid' if payment else 'Unpaid', reference=payment['reference'] if payment else None, paidDate=payment['paidDate'] if payment else None)
    access = list(db.execute(select(project_groups)).mappings())
    for p in result['projects']: p['accessGroupIds'] = [g['groupId'] for g in access if g['projectId']==p['id']]
    edges = list(db.execute(select(predecessors)).mappings())
    for t in result['tasks']: t['predecessors'] = [e['predecessorId'] for e in edges if e['taskId']==t['id']]
    result['updates'].sort(key=lambda r:r['createdAt'], reverse=True)
    result['audit'].sort(key=lambda r:r['at'], reverse=True)
    milestone_ids=set(db.execute(select(milestones.c.taskId)).scalars())
    for t in result['tasks']: t['isMilestone']=t['id'] in milestone_ids
    snapshots=[asdict(r) for r in db.execute(select(baseline_tasks)).mappings()]
    result['baselines']=[{**asdict(b),'tasks':[{k:v for k,v in t.items() if k!='baselineId'} for t in snapshots if t['baselineId']==b['id']]} for b in db.execute(select(baselines)).mappings()]
    result['version'] = db.execute(select(workspace.c.version).where(workspace.c.id==1)).scalar_one()
    return result

def lookup_id(db,kind,name):
    if name is None: return None
    table = LOOKUPS[kind]
    value = db.execute(select(table.c.id).where(table.c.name==name)).scalar_one_or_none()
    if value is None: raise ValueError(f'Unresolved {kind} lookup. Review migration/master data.')
    return value

def user_values(db,row):
    return {k:row[k] for k in ('id','email','name','role','active')} | {'departmentId':lookup_id(db,'department',row['department'])}

def insert_user(db,row):
    db.execute(insert(users).values(**user_values(db,row)))
    db.execute(insert(credentials).values(userId=row['id'],password_hash=row['password_hash']))

def row_values(db,key,row,actor_id=None):
    table = TABLES[key]
    values = {c.name:row.get(c.name) for c in table.columns}
    if key=='masterProjects': values['primaryDepartmentId']=lookup_id(db,'department',row.get('primaryDepartment'))
    if key=='projects': values['departmentId']=lookup_id(db,'department',row['department'])
    if key=='tasks': values['resourceId']=lookup_id(db,'resource',row['resource'])
    if key=='pos': values['vendorId']=lookup_id(db,'vendor',row['vendor'])
    if key=='updates': values['authorId']=row.get('authorId') or actor_id
    return values

def persist_changes(db,old,new,actor_id=None):
    from .catalogs import catalog_rows
    from .access import with_access
    new = with_access({**new,'catalogs':catalog_rows(new)})
    previous_catalogs = {r['id']:r for r in old.get('catalogs',[])}
    for row in new['catalogs']:
        table=LOOKUPS[row['kind']]; prior=previous_catalogs.get(row['id'])
        if prior==row: continue
        values={k:row[k] for k in ('id','name','active')}
        db.execute((update(table).where(table.c.id==row['id']) if prior else insert(table)).values(**values))
    for row in new.get('users',[]):
        original=next((x for x in old.get('users',[]) if x['id']==row['id']),None)
        if not original or original==row: continue
        db.execute(update(users).where(users.c.id==row['id']).values(**user_values(db,row)))
        if row['id']!=actor_id and any(original[k]!=row[k] for k in ['role','department','active','email']):
            db.execute(delete(sessions).where(sessions.c.user_id==row['id']))
    for key,table in TABLES.items():
        previous={r['id']:r for r in old.get(key,[])}
        rows=list(new[key])
        if key=='tasks':
            # Insert parents before children even when imported IDs are unordered.
            ordered=[];done=set(previous)
            while rows:
                ready=[r for r in rows if not r.get('parentId') or r['parentId'] in done]
                if not ready: raise ValueError('Task parent cycle or missing parent.')
                ordered.extend(ready);done.update(r['id'] for r in ready);rows=[r for r in rows if r not in ready]
            rows=ordered
        for row in rows:
            original=previous.get(row['id'])
            if original==row: continue
            values=row_values(db,key,row,actor_id)
            if original:
                if key=='changeRequests' and (original['status']!='Pending' or any(row.get(k)!=original.get(k) for k in ['projectId','title','reason','amount','requestedById','requestedBy','requestedDate'])): raise RuntimeError('Submitted requests and final decisions are immutable.')
                if key in ['audit','updates']: raise RuntimeError('Audit and progress records are append-only.')
                # A renamed lookup changes the API display but not its referencing row.
                if values=={c.name:original.get(c.name) for c in table.columns}: continue
                db.execute(update(table).where(table.c.id==row['id']).values(**values))
            else: db.execute(insert(table).values(**values))
    for key,table,pk,fields in [('consultants',consultant_details,'consultantId',['designation']),('trips',trip_costs,'tripId',['flightCostJod','hotelBookedBy','hotelCostJod','visaCostJod'])]:
        for row in new[key]:
            if key=='trips' and 'visaCostJod' not in row: continue
            values={k:row.get(k,'' if k=='designation' else None) for k in fields}
            prior=next((x for x in old.get(key,[]) if x['id']==row['id']),{})
            if prior and all(prior.get(k)==v for k,v in values.items()): continue
            exists=db.execute(select(table.c[pk]).where(table.c[pk]==row['id'])).scalar_one_or_none()
            db.execute((update(table).where(table.c[pk]==row['id']) if exists else insert(table)).values(**{pk:row['id'],**values}))
    for p in new['projects']:
        values={k:p.get(k) for k in ['currency','usdRate','rateDate','vendorId']}
        exists=db.execute(select(project_finance.c.projectId).where(project_finance.c.projectId==p['id'])).scalar_one_or_none()
        prior=next((r for r in old.get('projects',[]) if r['id']==p['id']),{})
        if exists and all(prior.get(k)==v for k,v in values.items()): continue
        db.execute((update(project_finance).where(project_finance.c.projectId==p['id']) if exists else insert(project_finance)).values(projectId=p['id'],**values))
    for row in new['invoices']:
        if row.get('changeRequestId') and not any(i['id']==row['id'] and i.get('changeRequestId')==row['changeRequestId'] for i in old.get('invoices',[])):
            db.execute(insert(invoice_changes).values(invoiceId=row['id'],changeRequestId=row['changeRequestId']))
        if row.get('termId') and not any(i['id']==row['id'] and i.get('termId')==row['termId'] for i in old.get('invoices',[])):
            db.execute(insert(invoice_terms).values(invoiceId=row['id'],termId=row['termId']))
        prior=next((x for x in old.get('invoices',[]) if x['id']==row['id']),None)
        if row['status']=='Paid' and (not prior or prior['status']!='Paid'):
            db.execute(insert(payments).values(invoiceId=row['id'],reference=row['reference'],paidDate=row['paidDate'],recordedById=actor_id))
    for p in new['projects']:
        prior=next((x for x in old.get('projects',[]) if x['id']==p['id']),None)
        if prior and prior.get('offDays',[])==p.get('offDays',[]): continue
        db.execute(delete(project_days_off).where(project_days_off.c.projectId==p['id']))
        for day in p.get('offDays',[]): db.execute(insert(project_days_off).values(projectId=p['id'],weekday=day))
    for p in new['projects']:
        prev=next((x for x in old.get('projects',[]) if x['id']==p['id']),None)
        if prev and prev.get('accessGroupIds',[])==p['accessGroupIds']: continue
        db.execute(delete(project_groups).where(project_groups.c.projectId==p['id']))
        for group_id in p['accessGroupIds']: db.execute(insert(project_groups).values(projectId=p['id'],groupId=group_id))
    for t in new['tasks']:
        prev=next((x for x in old.get('tasks',[]) if x['id']==t['id']),None)
        if prev and prev['predecessors']==t['predecessors']: continue
        db.execute(delete(predecessors).where(predecessors.c.taskId==t['id']))
        for pred in t['predecessors']: db.execute(insert(predecessors).values(taskId=t['id'],predecessorId=pred))

    for t in new['tasks']:
        prior=next((x for x in old.get('tasks',[]) if x['id']==t['id']),{})
        if bool(prior.get('isMilestone'))==bool(t.get('isMilestone')): continue
        if t.get('isMilestone'): db.execute(insert(milestones).values(taskId=t['id']))
        else: db.execute(delete(milestones).where(milestones.c.taskId==t['id']))
    prior_baselines={b['id']:b for b in old.get('baselines',[])}
    if not set(prior_baselines).issubset({b['id'] for b in new.get('baselines',[])}): raise RuntimeError('Baselines cannot be deleted.')
    for baseline in new.get('baselines',[]):
        prior=prior_baselines.get(baseline['id'])
        if prior:
            if prior!=baseline: raise RuntimeError('Baselines are immutable.')
            continue
        db.execute(insert(baselines).values(**{c.name:baseline[c.name] for c in baselines.columns}))
        for task in baseline['tasks']: db.execute(insert(baseline_tasks).values(baselineId=baseline['id'],**task))


def lock_workspace(db,write=True):
    """A short, shared serialization boundary for reads and all security writes.

    SQL Server locks last until this transaction commits. The portfolio is small;
    this deliberately favors consistent authorization over concurrent writers.
    """
    query=select(workspace.c.version).where(workspace.c.id==1)
    if db.dialect.name=='mssql':
        query=query.with_hint(workspace,'WITH (UPDLOCK, HOLDLOCK)' if write else 'WITH (HOLDLOCK)',dialect_name='mssql')
    db.execute(query).scalar_one()
