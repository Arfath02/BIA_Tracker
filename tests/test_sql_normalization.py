"""Relational integrity and preserving migration tests. SQLite is test-only;
SQL Server DDL compilation is an additional gate, not server execution.
"""
import json, os
from pathlib import Path
from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine, event, insert, select, text, inspect, func
from sqlalchemy.exc import IntegrityError
from production import database as d
import legacy_schema as legacy
from production.migrations import initialize
from production.catalogs import catalog_rows

@pytest.fixture
def db_engine(monkeypatch):
    monkeypatch.setenv('BIA_TESTING','1')
    engine=d.engine_for('sqlite://')
    initialize(engine)
    yield engine
    engine.dispose()

def test_normalized_shape_and_sqlserver_ddl():
    from sqlalchemy.schema import CreateTable,CreateIndex
    from sqlalchemy.dialects import mssql
    assert len(d.metadata.tables)==24
    assert 'data' not in d.workspace.c
    assert 'password_hash' not in d.users.c and 'department' not in d.users.c
    assert 'department' not in d.tasks.c and 'resource' not in d.tasks.c
    assert 'vendor' not in d.pos.c
    assert not {'status','reference','paidDate'} & set(d.invoices.c.keys())
    for table in d.metadata.sorted_tables:
        assert table.primary_key.columns
        sql=str(CreateTable(table).compile(dialect=mssql.dialect()))
        assert 'CREATE TABLE bia.' in sql
        for index in table.indexes: assert str(CreateIndex(index).compile(dialect=mssql.dialect()))
    assert 'start DATE NOT NULL' in str(CreateTable(d.projects).compile(dialect=mssql.dialect()))
    assert 'DATETIME2(6)' in str(CreateTable(d.audit).compile(dialect=mssql.dialect()))
    assert next(iter(d.project_groups.c.groupId.foreign_keys)).target_fullname=='bia.departments.id'

def test_foreign_keys_and_row_constraints(db_engine):
    with db_engine.begin() as db:
        digital=db.execute(select(d.departments.c.id).where(d.departments.c.name=='Digital & IT')).scalar_one()
        resource=db.execute(select(d.resources.c.id)).scalar_one()
        p=dict(id='p1',masterId='bia-digital-transformation',title='One',departmentId=digital,owner='Lead',budget=100,start='2026-01-01',due='2026-12-31')
        db.execute(insert(d.projects).values(**p));db.execute(insert(d.projects).values(**{**p,'id':'p2'}))
        t=dict(id='t1',projectId='p1',title='Parent',resourceId=resource,effort=1,start='2026-01-01',due='2026-12-31',progress=0,blocked=False)
        db.execute(insert(d.tasks).values(**t))
    bad=[(d.projects,{**p,'id':'bad','departmentId':'missing'}),
         (d.projects,{**p,'id':'bad','budget':-1}),
         (d.projects,{**p,'id':'bad','due':'2025-01-01'}),
         (d.tasks,{**t,'id':'bad','projectId':'p2','parentId':'t1'}),
         (d.tasks,{**t,'id':'bad','parentId':'bad'}),
         (d.tasks,{**t,'id':'bad','progress':101}),
         (d.tasks,{**t,'id':'bad','progress':100,'blocked':True}),
         (d.tasks,{**t,'id':'bad','effort':0}),
         (d.project_groups,{'projectId':'p1','groupId':resource}),
         (d.predecessors,{'taskId':'t1','predecessorId':'t1'})]
    for table,row in bad:
        with pytest.raises(IntegrityError):
            with db_engine.begin() as db: db.execute(insert(table).values(**row))

def legacy_engine():
    engine=create_engine('sqlite://',execution_options={'schema_translate_map':{'bia':'normalized'}})
    @event.listens_for(engine,'connect')
    def attach(connection,record):
        connection.execute("ATTACH DATABASE ':memory:' AS normalized")
        connection.execute('PRAGMA foreign_keys=ON')
    return engine

def load_v6(engine):
    legacy.metadata.create_all(engine)
    seed=json.loads(Path('production/seed.json').read_text())
    from production.access import with_access
    seed=with_access(seed);seed['catalogs']=catalog_rows(seed)
    with engine.begin() as db:
        db.execute(insert(legacy.workspace).values(id=1,version=22))
        db.execute(insert(legacy.users).values(id='admin',email='admin@example.test',name='Admin',role='admin',department='Digital & IT',active=True,password_hash='preserved-test-hash'))
        for key,table in legacy.TABLES.items():
            for row in seed[key]:
                db.execute(insert(table).values(**{c.name:row.get(c.name) for c in table.columns}))
        for task in seed['tasks']:
            for pred in task['predecessors']: db.execute(insert(legacy.predecessors).values(taskId=task['id'],predecessorId=pred))
        db.execute(insert(legacy.sessions).values(token='a'*64,user_id='admin',expires=9999999999))
    return seed

def test_v6_copy_preserves_data_and_leaves_legacy(db_engine):
    engine=legacy_engine();source=load_v6(engine)
    initialize(engine);initialize(engine)
    with engine.connect() as db:
        state=d.read_state(db)
        assert state['version']==22
        for key in d.TABLES: assert {r['id'] for r in state[key]}=={r['id'] for r in source[key]}
        assert db.execute(select(d.credentials.c.password_hash)).scalar_one()=='preserved-test-hash'
        assert db.execute(select(func.count()).select_from(d.sessions)).scalar_one()==0
        assert db.execute(select(func.count()).select_from(legacy.sessions)).scalar_one()==1
        assert db.execute(select(func.count()).select_from(legacy.projects)).scalar_one()==len(source['projects'])
        assert db.execute(select(func.count()).select_from(d.payments)).scalar_one()==sum(i['status']=='Paid' for i in source['invoices'])
        assert all(not u['authorId'] for u in state['updates'])
        assert all(p['createdById'] is None and p['accessGroupIds']==[] for p in state['projects'])
    engine.dispose()

def test_v1_missing_columns_backfill_and_unassigned_master():
    engine=legacy_engine()
    with engine.begin() as db:
        db.execute(text('CREATE TABLE workspace (id INTEGER PRIMARY KEY, version INTEGER NOT NULL)'))
        db.execute(text('INSERT INTO workspace VALUES(1,9)'))
        db.execute(text('CREATE TABLE master_projects (id VARCHAR(36) PRIMARY KEY, title NVARCHAR(100), owner NVARCHAR(80), description NVARCHAR(1000))'))
        db.execute(text("INSERT INTO master_projects VALUES ('bia-digital-transformation','BIA Digital Transformation','Original lead','Keep'),('other','Other','Other lead','Keep')"))
        db.execute(text('CREATE TABLE projects (id VARCHAR(36) PRIMARY KEY, title NVARCHAR(100), department NVARCHAR(60), owner NVARCHAR(80), budget NUMERIC(18,2), start VARCHAR(10), due VARCHAR(10), description NVARCHAR(1000), color VARCHAR(10))'))
        db.execute(text("INSERT INTO projects VALUES('legacy','Legacy','Custom department','Owner',100,'2026-01-01','2026-12-31','','#b31c3f')"))
        db.execute(text('CREATE TABLE audit_log (id VARCHAR(36) PRIMARY KEY, actor NVARCHAR(80), role VARCHAR(20), action NVARCHAR(500), at VARCHAR(40))'))
        db.execute(text("INSERT INTO audit_log VALUES('old-audit','Original user','admin','Original event','2026-09-01T00:00:00Z')"))
    initialize(engine);initialize(engine)
    with engine.connect() as db:
        state=d.read_state(db)
        assert state['version']==9 and state['projects'][0]['masterId']=='bia-digital-transformation'
        assert next(m for m in state['masterProjects'] if m['id']=='other')['primaryDepartment'] is None
        assert next(m for m in state['masterProjects'] if m['id']=='bia-digital-transformation')['owner']=='Original lead'
        assert state['audit'][0]['actorId'] is None and state['audit'][0]['action']=='Original event'
        assert 'masterId' not in {c['name'] for c in inspect(db).get_columns('projects')}
    engine.dispose()

def test_migration_fails_closed_for_ambiguous_catalogs():
    engine=legacy_engine();load_v6(engine)
    with engine.begin() as db: db.execute(insert(legacy.catalogs).values(id='ambiguous',kind='department',name='digital & it',active=True))
    with pytest.raises(RuntimeError,match='Duplicate'): initialize(engine)
    with engine.connect() as db:
        assert db.execute(select(legacy.workspace.c.version)).scalar_one()==22
        assert not inspect(db).has_table('schema_migrations',schema='normalized')
    engine.dispose()

def test_production_rejects_insecure_sql_connections(monkeypatch):
    monkeypatch.delenv('BIA_TESTING',raising=False)
    for url in ['sqlite://','mssql+pyodbc://user:secret@host/db?driver=ODBC+Driver+18+for+SQL+Server', 'mssql+pyodbc://user:secret@host/db?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=no&TrustServerCertificate=yes']:
        with pytest.raises(RuntimeError): d.engine_for(url)

def test_migration_rejects_unrecognized_legacy_customization():
    engine=legacy_engine();load_v6(engine)
    with engine.begin() as db: db.execute(text('ALTER TABLE projects ADD confidential_code VARCHAR(30)'))
    with pytest.raises(RuntimeError,match='Customized legacy columns'): initialize(engine)
    with engine.connect() as db: assert db.execute(select(legacy.workspace.c.version)).scalar_one()==22
    from production.migrations import known_legacy_check
    assert known_legacy_check('users',"([role]='management' OR [role]='executive' OR [role]='finance' OR [role]='delegate' OR [role]='head' OR [role]='admin')")
    assert not known_legacy_check('users',"role IN ('admin','head','delegate','finance','executive') AND active=1")
    assert not known_legacy_check('projects','budget>=0 AND budget<=100')
    engine.dispose()

def test_v7_upgrade_preserves_existing_rows_and_is_repeatable(db_engine):
    from sqlalchemy import delete
    with db_engine.begin() as db:
        before=d.read_state(db)
        for table in [d.baseline_tasks,d.baselines,d.milestones]: table.drop(db)
        db.execute(delete(d.schema_migrations))
        db.execute(insert(d.schema_migrations).values(version=7,appliedAt=datetime.now(timezone.utc)))
    initialize(db_engine);initialize(db_engine)
    with db_engine.connect() as db:
        after=d.read_state(db)
        assert after==before
        assert set(db.execute(select(d.schema_migrations.c.version)).scalars())=={7,9}


def test_v8_calendar_upgrade_is_preserving(db_engine):
    from sqlalchemy import delete
    with db_engine.begin() as db:
        before=d.read_state(db)
        d.project_days_off.drop(db)
        db.execute(delete(d.schema_migrations))
        db.execute(insert(d.schema_migrations).values(version=8,appliedAt=datetime.now(timezone.utc)))
    initialize(db_engine);initialize(db_engine)
    with db_engine.connect() as db:
        assert d.read_state(db)==before
        assert set(db.execute(select(d.schema_migrations.c.version)).scalars())=={8,9}
