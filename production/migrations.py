"""Explicit, transactional v1-v6 -> v7 copy. Never drops or rewrites legacy tables."""
from datetime import datetime, timezone
import re
from uuid import uuid4
from sqlalchemy import inspect, select, insert, Table, MetaData, text, func
from . import database as d
from .catalogs import catalog_rows
from .access import with_access
from .masters import default_master

LEGACY_COLUMNS = {
 'workspace':'id version', 'users':'id email name role department active password_hash',
 'master_projects':'id title primaryDepartment owner description',
 'projects':'id masterId createdById title department owner budget start due description color',
 'tasks':'id projectId parentId title department assigneeId resource effort start due progress blocked',
 'task_predecessors':'taskId predecessorId', 'purchase_orders':'id projectId number vendor amount date description',
 'invoices':'id poId number amount date due status reference paidDate',
 'progress_updates':'id taskId progress note author createdAt', 'audit_log':'id projectId actorId actor role action at',
 'sessions':'token user_id expires', 'login_attempts':'key count expires',
 'catalogs':'id kind name active', 'project_department_access':'projectId groupId'}

def known_legacy_check(table, expression):
    normalized=re.sub(r'[\s\[\]()]','',expression).lower()
    simple={'workspace':{'id=1'},'projects':{'budget>=0'},'tasks':{'progress>=0andprogress<=100','effort>0'},'task_predecessors':{'taskid<>predecessorid'},'purchase_orders':{'amount>0'},'invoices':{'amount>0'}}
    if normalized in simple.get(table,set()): return True
    enum={'users':('role',{'admin','head','delegate','finance','executive'}), 'invoices':('status',{'Paid','Unpaid'}), 'catalogs':('kind',{'department','vendor','resource'})}.get(table)
    if not enum: return False
    column,expected=enum;values=set(re.findall(r"'([^']*)'",expression))
    identifiers={v.lower() for v in re.findall(r'[a-zA-Z_]+',re.sub(r"N?'[^']*'",'',expression))}
    enum_syntax=rf"{column}in(?:n?'[^']*',)*n?'[^']*'|{column}=n?'[^']*'(?:or{column}=n?'[^']*')*"
    return bool(re.fullmatch(enum_syntax,normalized)) and values in (expected, expected|{'management'} if table=='users' else expected) and not identifiers-{column,'in','or'}

def verify_legacy_shape(db, inspector, tables, schema):
    for name in tables & LEGACY_COLUMNS.keys():
        extra={c['name'] for c in inspector.get_columns(name,schema=schema)}-set(LEGACY_COLUMNS[name].split())
        if extra: raise RuntimeError('Customized legacy columns in '+name+'; DBA migration review required.')
        for check in inspector.get_check_constraints(name,schema=schema):
            if not known_legacy_check(name,check['sqltext']): raise RuntimeError('Customized legacy constraint in '+name+'; DBA migration review required.')
    if db.dialect.name=='mssql':
        customized=db.execute(text("SELECT COUNT(*) FROM sys.triggers WHERE parent_class=1 AND OBJECT_SCHEMA_NAME(parent_id)=N'dbo'")).scalar_one()
        policies=db.execute(text('SELECT COUNT(*) FROM sys.security_policies')).scalar_one()
        if customized or policies: raise RuntimeError('Custom triggers or row security found; DBA migration review required.')

def target_schema(db):
    return db.get_execution_options().get('schema_translate_map', {}).get('bia', 'bia')

def legacy_snapshot(db):
    inspector=inspect(db)
    # SQL Server's former application tables are in dbo. SQLite is test-only.
    source_schema='dbo' if db.dialect.name=='mssql' else None
    tables=set(inspector.get_table_names(schema=source_schema))
    if 'workspace' not in tables or ('users' not in tables and 'projects' not in tables): return None
    if source_schema==target_schema(db): return None
    verify_legacy_shape(db,inspector,tables,source_schema)
    def rows(name):
        if name not in tables: return []
        table=Table(name,MetaData(),schema=source_schema,autoload_with=db)
        return [d.asdict(r) for r in db.execute(select(table)).mappings()]
    workspace=rows('workspace')
    if len(workspace)!=1 or workspace[0]['id']!=1: raise RuntimeError('Unexpected legacy workspace; DBA review required.')
    state={key:rows(name) for key,name in {'masterProjects':'master_projects','projects':'projects','tasks':'tasks','pos':'purchase_orders','invoices':'invoices','updates':'progress_updates','audit':'audit_log','users':'users'}.items()}
    if not state['masterProjects']: state.pop('masterProjects')
    if 'catalogs' in tables: state['catalogs']=rows('catalogs')
    if not state.get('catalogs'): state.pop('catalogs',None)
    state['version']=workspace[0]['version']
    edges=rows('task_predecessors');grants=rows('project_department_access')
    for task in state['tasks']: task['predecessors']=[e['predecessorId'] for e in edges if e['taskId']==task['id']]
    for project in state['projects']: project['accessGroupIds']=[g['groupId'] for g in grants if g['projectId']==project['id']]
    state=with_access(state);state['catalogs']=catalog_rows(state)
    # Historical vendor/resource names may no longer be in the dropdown. Preserve
    # their identity as inactive values, never guess a new vendor from a rename.
    references={'department':[u['department'] for u in state['users']]+[p['department'] for p in state['projects']]+[m.get('primaryDepartment') for m in state['masterProjects']], 'vendor':[p['vendor'] for p in state['pos']], 'resource':[t['resource'] for t in state['tasks']]}
    for kind,names in references.items():
        known={c['name'] for c in state['catalogs'] if c['kind']==kind}
        for name in dict.fromkeys(n for n in names if n):
            if name not in known:
                state['catalogs'].append(dict(id=str(uuid4()),kind=kind,name=name,active=False));known.add(name)
    # Stop on ambiguity even on a case-sensitive test database.
    keys=[(c['kind'],c['name'].casefold()) for c in state['catalogs']]
    if len(keys)!=len(set(keys)): raise RuntimeError('Duplicate case-insensitive lookup names; DBA reconciliation required.')
    for table,key in [('users','email'),('masterProjects','title'),('pos','number')]:
        names=[r[key].casefold() for r in state[table]]
        if len(names)!=len(set(names)): raise RuntimeError(f'Duplicate {table} {key}; DBA reconciliation required.')
    project_map={p['id']:p for p in state['projects']}
    for task in state['tasks']:
        if task.get('department') != project_map[task['projectId']]['department']:
            raise RuntimeError('Legacy task/project department mismatch; DBA reconciliation required.')
    return state

def empty_state():
    s=dict(masterProjects=[default_master()],projects=[],tasks=[],pos=[],invoices=[],updates=[],audit=[],users=[],version=1)
    s['catalogs']=catalog_rows(s)
    return s

def initialize(engine):
    with engine.begin() as db:
        if db.dialect.name=='mssql':
            db.execute(text('SET XACT_ABORT ON'))
            lock=db.execute(text("DECLARE @result int; EXEC @result=sys.sp_getapplock @Resource=N'BIA schema v7 migration', @LockMode='Exclusive', @LockOwner='Transaction', @LockTimeout=0; SELECT @result;")).scalar_one()
            if lock<0: raise RuntimeError('Another migration is running.')
            if not db.execute(text("SELECT SCHEMA_ID(N'bia')")).scalar_one_or_none():
                db.execute(text('CREATE SCHEMA bia AUTHORIZATION dbo'))
        inspector=inspect(db)
        schema=target_schema(db)
        if inspector.has_table('schema_migrations',schema=schema):
            versions=list(db.execute(select(d.schema_migrations.c.version)).scalars())
            if versions and max(versions)>d.SCHEMA_VERSION: raise RuntimeError('Database is newer than this application.')
            if d.SCHEMA_VERSION in versions:
                print('Current schema already installed; no data changed.');return
            if 7 in versions or 8 in versions:
                d.metadata.create_all(db, tables=[d.milestones,d.baselines,d.baseline_tasks,d.project_days_off])
                db.execute(insert(d.schema_migrations).values(version=d.SCHEMA_VERSION,appliedAt=datetime.now(timezone.utc)))
                print('Schema v9 installed; original plans preserved. No baseline was assumed or created.');return
        source=legacy_snapshot(db)
        d.metadata.create_all(db)
        # Refuse partially populated targets; don't merge unrelated installations.
        for table in d.metadata.sorted_tables:
            if db.execute(select(func.count()).select_from(table)).scalar_one():
                raise RuntimeError('Unversioned target schema contains data. Restore/reconcile it before migration.')
        db.execute(insert(d.roles),d.ROLE_ROWS)
        state=source or empty_state()
        for row in state['catalogs']:
            db.execute(insert(d.LOOKUPS[row['kind']]).values(**{k:row[k] for k in ('id','name','active')}))
        for row in state['users']: d.insert_user(db,row)
        old={'catalogs':state['catalogs'],'users':state['users']}
        d.persist_changes(db,old,state)
        db.execute(insert(d.workspace).values(id=1,version=state['version']))
        actual=d.read_state(db)
        for key in d.TABLES:
            if {r['id'] for r in actual[key]}!={r['id'] for r in state[key]}:
                raise RuntimeError('Migration verification failed for '+key)
        for key,field in [('projects','budget'),('pos','amount'),('invoices','amount')]:
            from decimal import Decimal
            before=sum(Decimal(str(r[field])) for r in state[key])
            after=sum(Decimal(str(r[field])) for r in actual[key])
            if before!=after: raise RuntimeError('Financial reconciliation failed for '+key)
        if {i['id'] for i in actual['invoices'] if i['status']=='Paid'}!={i['id'] for i in state['invoices'] if i['status']=='Paid'}:
            raise RuntimeError('Payment reconciliation failed.')
        db.execute(insert(d.schema_migrations).values(version=d.SCHEMA_VERSION,appliedAt=datetime.now(timezone.utc)))
    print('Schema v8 ready: normalized tables installed; legacy tables preserved; old sessions not copied.')
