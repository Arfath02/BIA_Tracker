"""FastAPI service for the Ubuntu + Microsoft SQL Server deployment."""
import os, time, hashlib, secrets, re, logging
from datetime import datetime,timezone
from uuid import uuid4
from typing import Literal
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select,insert,update,delete,func
from sqlalchemy.exc import IntegrityError
from . import database as d
from .domain import mutate,ROLES,reject
from .catalogs import allowed,catalog_rows
from .access import visible_state

engine=d.engine_for(os.environ.get('DATABASE_URL'))
origins={v.strip().rstrip('/') for v in os.getenv('TRUSTED_ORIGINS','').split(',') if v.strip()}
if not origins: raise RuntimeError('TRUSTED_ORIGINS must name the exact HTTPS application origin.')
TESTING=os.getenv('BIA_TESTING')=='1'
if not TESTING and any(not v.startswith('https://') for v in origins): raise RuntimeError('Production origins must use HTTPS.')
ph=PasswordHasher(time_cost=3,memory_cost=65536,parallelism=2)
dummy_hash=ph.hash(secrets.token_urlsafe(32))
app=FastAPI(title='BIA Digital Transformation API',docs_url='/api/docs' if TESTING else None,redoc_url=None,openapi_url='/api/openapi.json' if TESTING else None)
class Account(BaseModel):
    model_config=ConfigDict(extra='forbid')
    name:str=Field(min_length=1,max_length=80)
    email:str=Field(min_length=3,max_length=254)
    password:str=Field(min_length=12,max_length=128)
    role:Literal['admin','management','head','delegate','finance','executive']
    department:str
    version:int|None=Field(default=None,ge=1,strict=True)
class Login(BaseModel):
    email:str=Field(max_length=254)
    password:str=Field(max_length=128)
class Command(BaseModel):
    model_config=ConfigDict(extra='forbid')
    action:Literal['project','task','update','po','invoice','payment','catalog','user_edit','master','project_access','baseline','project_dates','project_calendar']
    version:int=Field(ge=1,strict=True)
    payload:dict
class Active(BaseModel):
    id:str
    active:bool=Field(strict=True)
class ResetPassword(BaseModel):
    id:str
    password:str=Field(min_length=12,max_length=128)
    version:int=Field(ge=1,strict=True)
class Password(BaseModel):
    current:str=Field(max_length=128)
    password:str=Field(min_length=12,max_length=128)

@app.exception_handler(HTTPException)
async def http_error(request,ex): return JSONResponse({'error':str(ex.detail)},status_code=ex.status_code)
@app.exception_handler(IntegrityError)
async def conflict(request,ex): return JSONResponse({'error':'The record conflicts with existing data. Refresh and try again.'},status_code=409)
from fastapi.exceptions import RequestValidationError
@app.exception_handler(RequestValidationError)
async def validation(request,ex): return JSONResponse({'error':'Check required fields, data types and allowed values.'},status_code=422)
@app.middleware('http')
async def security(request,call_next):
    if request.method not in ['GET','HEAD']:
        origin = request.headers.get('origin', '').rstrip('/')
        host = request.headers.get('host', '')
        same_host = origin in (f'http://{host}', f'https://{host}') or not origin
        if (origin not in origins and not same_host and not TESTING) or request.headers.get('x-bia-request') != '1': return JSONResponse({'error':'Cross-origin or invalid request denied.'},403)
        if not request.headers.get('content-type','').startswith('application/json'): return JSONResponse({'error':'JSON body required.'},415)
        try: size=int(request.headers.get('content-length','0'))
        except ValueError: return JSONResponse({'error':'Invalid request size.'},400)
        if size<0 or size>20000: return JSONResponse({'error':'Request is too large.'},413)
        chunks=[];size=0
        async for chunk in request.stream():
            size+=len(chunk)
            if size>20000: return JSONResponse({'error':'Request is too large.'},413)
            chunks.append(chunk)
        request._body=b''.join(chunks)
    try: response=await call_next(request)
    except Exception as e:
        event_id=secrets.token_hex(8)
        logging.getLogger('bia.security').error('Unhandled API error; event=%s path=%s: %s',event_id,request.url.path,e,exc_info=True)
        response=JSONResponse({'error':'Unable to complete this request. Contact the administrator with reference '+event_id+'.'},status_code=500)
    for k,v in {'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'same-origin','Content-Security-Policy':"default-src 'none'; frame-ancestors 'none'",'Strict-Transport-Security':'max-age=31536000'}.items(): response.headers[k]=v
    return response

def token_hash(token): return hashlib.sha256(token.encode()).hexdigest()
def safe_user(row): return {k:v for k,v in dict(row).items() if k!='password_hash'}
def auth_select():
    return d.user_select().add_columns(d.credentials.c.password_hash).join(d.credentials,d.credentials.c.userId==d.users.c.id)
def who(db,req,required=True):
    token=req.cookies.get('bia_session','')
    row=db.execute(d.user_select().join(d.sessions,d.sessions.c.user_id==d.users.c.id).where(d.sessions.c.token==token_hash(token),d.sessions.c.expires>int(time.time()),d.users.c.active==True)).mappings().first() if token else None
    if not row and required: reject('Sign in to save changes.',401)
    return safe_user(row) if row else None

def audit(db,user,action): db.execute(insert(d.audit).values(id=str(uuid4()),actorId=user['id'],actor=user['name'],role=user['role'],action=action,at=datetime.now(timezone.utc).isoformat()))
def session(db,user):
    token=secrets.token_urlsafe(48)
    db.execute(delete(d.sessions).where(d.sessions.c.expires<int(time.time())))
    db.execute(insert(d.sessions).values(token=token_hash(token),user_id=user['id'],expires=int(time.time())+28800))
    response=JSONResponse({'user':safe_user(user)});response.set_cookie('bia_session',token,httponly=True,secure=not TESTING,samesite='strict',max_age=28800,path='/');return response

def validated_account(b,s):
    name=b.name.strip();email=b.email.strip().lower()
    if not name or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email): reject('Enter a name and valid email address.')
    if not allowed(s,'department',b.department): reject('Select a valid department.')
    return dict(id=str(uuid4()),name=name,email=email,role=b.role,department=b.department,active=True,password_hash=ph.hash(b.password))

def rate_limit(db,key):
    now=int(time.time());db.execute(delete(d.attempts).where(d.attempts.c.expires<now));row=db.execute(select(d.attempts).where(d.attempts.c.key==key)).mappings().first()
    if row and row['expires']>now and row['count']>=8: reject('Too many attempts. Try again in 15 minutes.',429)
    if row: db.execute(update(d.attempts).where(d.attempts.c.key==key).values(count=d.attempts.c.count+1 if row['expires']>now else 1,expires=row['expires'] if row['expires']>now else now+900))
    else: db.execute(insert(d.attempts).values(key=key,count=1,expires=now+900))

@app.get('/api/health')
def health():
    with engine.connect() as db:
        db.execute(select(d.workspace.c.version).where(d.workspace.c.id==1)).scalar_one()
        if db.execute(select(d.schema_migrations.c.version).where(d.schema_migrations.c.version==d.SCHEMA_VERSION)).scalar_one_or_none()!=d.SCHEMA_VERSION: reject('Schema upgrade required.',503)
    return {'status':'ok'}
@app.get('/api/state')
def state(request:Request):
    with engine.begin() as db:
        d.lock_workspace(db,write=False)
        user=who(db,request,False)
        if not user: return {'masterProjects':[],'projects':[],'tasks':[],'pos':[],'invoices':[],'users':[],'updates':[],'audit':[],'version':1,'demo':True,'setupRequired':False,'user':None}
        s=d.read_state(db);user=next((u for u in s['users'] if u['id']==user['id'] and u['active']),None)
        if not user: reject('Sign in again.',401)
        return {**visible_state(s,user),'demo':False,'setupRequired':False,'user':user}
@app.post('/api/setup')
def setup(): reject('The initial administrator is created by the server operator.',403)
@app.post('/api/login')
def login(b:Login,request:Request):
    email=b.email.strip().lower();key=token_hash(email)
    with engine.begin() as db:
        d.lock_workspace(db)
        rate_limit(db,key)
        row=db.execute(auth_select().where(d.users.c.email==email)).mappings().first()
    try: ok=ph.verify(row['password_hash'] if row else dummy_hash,b.password)
    except (VerifyMismatchError,VerificationError): ok=False
    if not ok or not row or not row['active']: reject('Email or password is incorrect.',401)
    with engine.begin() as db:
        d.lock_workspace(db)
        current=db.execute(auth_select().where(d.users.c.id==row['id'])).mappings().first()
        if not current or not current['active'] or current['password_hash']!=row['password_hash']: reject('Email or password is incorrect.',401)
        db.execute(delete(d.attempts).where(d.attempts.c.key==key));audit(db,current,'Signed in');return session(db,current)
@app.post('/api/logout')
def logout(request:Request):
    with engine.begin() as db:
        d.lock_workspace(db)
        db.execute(delete(d.sessions).where(d.sessions.c.token==token_hash(request.cookies.get('bia_session',''))))
    response=JSONResponse({'ok':True});response.delete_cookie('bia_session',path='/',httponly=True,secure=not TESTING,samesite='strict');return response
@app.post('/api/mutate')
def command(b:Command,request:Request):
    with engine.begin() as db:
        d.lock_workspace(db)
        old=d.read_state(db);user=who(db,request)
        if old['version']!=b.version: reject('Someone else updated the workspace. Refresh and try again.',409)
        new=mutate(old,user,b.action,b.payload)
        changed=db.execute(update(d.workspace).where(d.workspace.c.id==1,d.workspace.c.version==b.version).values(version=b.version+1))
        if changed.rowcount!=1: reject('Another update was saved first. Refresh and try again.',409)
        d.persist_changes(db,old,new,user['id'])
    return {'ok':True,'version':b.version+1,**({'masterId':b.payload.get('id') or new['masterProjects'][-1]['id']} if b.action=='master' else {})}
def claim_version(db,s,expected=None):
    if expected is not None and expected!=s['version']: reject('Someone else updated the workspace. Refresh and try again.',409)
    changed=db.execute(update(d.workspace).where(d.workspace.c.id==1,d.workspace.c.version==s['version']).values(version=s['version']+1))
    if changed.rowcount!=1: reject('Another update was saved first. Refresh and try again.',409)

@app.post('/api/users')
def create_user(b:Account,request:Request):
    with engine.begin() as db:
        d.lock_workspace(db)
        s=d.read_state(db);user=who(db,request)
        if user['role'] not in ['admin','head']: reject('Your role cannot manage accounts.',403)
        if user['role']=='head' and (b.role!='delegate' or b.department!=user['department']): reject('Heads can create delegates only in their own department.',403)
        target=validated_account(b,s);claim_version(db,s,b.version);d.insert_user(db,target);audit(db,user,'Created '+b.role+' account · '+target['name'])
    return {'ok':True}
@app.post('/api/users/active')
def active(b:Active,request:Request):
    with engine.begin() as db:
        d.lock_workspace(db)
        s=d.read_state(db);user=who(db,request);target=next((u for u in s['users'] if u['id']==b.id),None)
        if not target: reject('Account not found.',404)
        new=mutate(s,user,'user_edit',{**target,'active':b.active});claim_version(db,s);d.persist_changes(db,s,new,user['id'])
    return {'ok':True}
@app.post('/api/users/reset-password')
def reset_password(b:ResetPassword,request:Request):
    with engine.begin() as db:
        d.lock_workspace(db)
        s=d.read_state(db);user=who(db,request)
        if user['role']!='admin' or user['id']==b.id: reject('Only an administrator can reset another account’s password.',403)
        target=next((u for u in s['users'] if u['id']==b.id),None)
        if not target: reject('Account not found.',404)
        hashed=ph.hash(b.password);claim_version(db,s,b.version)
        db.execute(update(d.credentials).where(d.credentials.c.userId==b.id).values(password_hash=hashed));db.execute(delete(d.sessions).where(d.sessions.c.user_id==b.id));audit(db,user,'Reset password · '+target['name'])
    return {'ok':True}
@app.post('/api/password')
def password(b:Password,request:Request):
    with engine.begin() as db:
        d.lock_workspace(db)
        user=who(db,request);rate_limit(db,token_hash('password:'+user['id']))
    with engine.begin() as db:
        d.lock_workspace(db)
        user=who(db,request);row=db.execute(auth_select().where(d.users.c.id==user['id'])).mappings().one()
        try: ph.verify(row['password_hash'],b.current)
        except (VerifyMismatchError,VerificationError): reject('Current password is incorrect.')
        db.execute(update(d.credentials).where(d.credentials.c.userId==user['id']).values(password_hash=ph.hash(b.password)));db.execute(delete(d.sessions).where(d.sessions.c.user_id==user['id']));db.execute(delete(d.attempts).where(d.attempts.c.key==token_hash('password:'+user['id'])));audit(db,user,'Changed password');return session(db,user)
