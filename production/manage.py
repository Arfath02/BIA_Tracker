"""Operator commands. Web requests never create tables or migrate data."""
import os,sys,getpass
from sqlalchemy import select,text,update
from . import database as d
from .migrations import initialize

def main():
    engine=d.engine_for(os.environ.get('DATABASE_URL'));cmd=sys.argv[1] if len(sys.argv)>1 else ''
    if cmd in ['init','upgrade']: initialize(engine)
    elif cmd=='check-db':
        with engine.connect() as db:
            if engine.dialect.name=='mssql':
                row=db.execute(text("SELECT DB_NAME() AS db_name, SERVERPROPERTY('ProductVersion') AS version")).mappings().one()
                print('Connected to database:',row['db_name'],'— SQL Server',row['version'])
            else: print('Test database connection OK.')
    elif cmd=='create-admin':
        from .app import Account,validated_account
        name=input('Administrator name: ');email=input('Administrator email: ');pw=getpass.getpass('Password (12+ characters): ')
        if pw!=getpass.getpass('Confirm password: '): raise SystemExit('Passwords do not match.')
        with engine.begin() as db:
            d.lock_workspace(db)
            s=d.read_state(db);dept=next((x['name'] for x in s['catalogs'] if x['kind']=='department' and x['active']),None)
            if not dept: raise SystemExit('Initialize master data first.')
            row=validated_account(Account(name=name,email=email,password=pw,role='admin',department=dept),s)
            d.insert_user(db,row);db.execute(update(d.workspace).where(d.workspace.c.id==1).values(version=d.workspace.c.version+1))
        print('Administrator created. Sign in and open Admin portal.')
    else: raise SystemExit('Usage: python -m production.manage init | upgrade | check-db | create-admin')
if __name__=='__main__': main()
