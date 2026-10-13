import {visibleState} from '../src/access.js';
import {withMasters} from '../src/masters.js';
import {catalogRows,allowedChoice} from '../src/catalogs.js';
import {seed} from '../src/seed.js';
import {mutate,roles} from '../src/domain.js';
const encoder=new TextEncoder();
const hex=b=>[...new Uint8Array(b)].map(x=>x.toString(16).padStart(2,'0')).join('');
async function sha(s){return hex(await crypto.subtle.digest('SHA-256',encoder.encode(s)))}
async function hashPassword(password,salt){const key=await crypto.subtle.importKey('raw',encoder.encode(password),'PBKDF2',false,['deriveBits']);return hex(await crypto.subtle.deriveBits({name:'PBKDF2',salt:encoder.encode(salt),iterations:100000,hash:'SHA-256'},key,256))}
const safeUser=u=>u?{id:u.id,name:u.name,email:u.email,role:u.role,department:u.department,active:!!u.active}:null;
const json=(d,status=200,extra={})=>new Response(JSON.stringify(d),{status,headers:{'Content-Type':'application/json','Cache-Control':'no-store','X-Content-Type-Options':'nosniff',...extra}});
const err=(m,status=400)=>{throw Object.assign(new Error(m),{status})};
function validateAccount(b){if(typeof b.name!=='string'||!b.name.trim()||b.name.length>80)err('Enter a name, up to 80 characters.',422);if(typeof b.email!=='string'||b.email.length>254||!/^\S+@\S+\.\S+$/.test(b.email))err('Enter a valid email address.',422);if(typeof b.password!=='string'||b.password.length<12||b.password.length>128)err('Use a password of 12–128 characters.',422)}
async function userFor(req,db){const token=req.headers.get('Cookie')?.match(/(?:^|;\s*)bia_session=([^;]+)/)?.[1];if(!token)return null;return safeUser(await db.prepare('SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=? AND s.expires>? AND u.active=1').bind(await sha(token),Date.now()).first())}
async function readState(db){const initial=seed();await db.prepare('INSERT OR IGNORE INTO workspace(id,version,data) VALUES(1,1,?)').bind(JSON.stringify(initial)).run();const row=await db.prepare('SELECT data,version FROM workspace WHERE id=1').first();const users=(await db.prepare('SELECT id,email,name,role,department,active FROM users ORDER BY name').all()).results;const audit=(await db.prepare('SELECT * FROM access_audit ORDER BY at DESC LIMIT 200').all()).results;const s=JSON.parse(row.data);s.version=row.version;s.users=users.map(safeUser);s.audit=[...s.audit,...audit.map(a=>({...a,_access:true}))].sort((a,b)=>b.at.localeCompare(a.at));s.catalogs=catalogRows(s);return withMasters(s)}
async function newSession(db,u,req){const token=crypto.randomUUID()+crypto.randomUUID();await db.batch([db.prepare('DELETE FROM sessions WHERE expires<?').bind(Date.now()),db.prepare('INSERT INTO sessions(token,user_id,expires) VALUES(?,?,?)').bind(await sha(token),u.id,Date.now()+8*3600000)]);return json({user:safeUser(u)},200,{'Set-Cookie':`bia_session=${token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800${new URL(req.url).protocol==='https:'?'; Secure':''}`})}
// CAS and all dependent writes share one D1 transaction. A unique marker prevents
// side effects if a competing transaction claims the same workspace version first.
async function commitState(db,old,next,actor,extras=()=>[]){
 const marker=crypto.randomUUID(),guard="EXISTS (SELECT 1 FROM workspace WHERE id=1 AND json_extract(data,'$.lastMutation')=?)";
 const stored={...next,users:[],audit:next.audit.filter(a=>!a._access),lastMutation:marker};
 const statements=[db.prepare('UPDATE workspace SET data=?,version=version+1 WHERE id=1 AND version=?').bind(JSON.stringify(stored),old.version)];
 for(const u of next.users){const prior=old.users.find(x=>x.id===u.id);if(!prior||JSON.stringify(prior)===JSON.stringify(u))continue;
  statements.push(db.prepare(`UPDATE users SET name=?,email=?,role=?,department=?,active=? WHERE id=? AND ${guard}`).bind(u.name,u.email,u.role,u.department,u.active?1:0,u.id,marker));
  if(u.id!==actor.id&&(prior.role!==u.role||prior.department!==u.department||prior.active!==u.active||prior.email!==u.email))statements.push(db.prepare(`DELETE FROM sessions WHERE user_id=? AND ${guard}`).bind(u.id,marker));
 }
 statements.push(...extras(guard,marker));const result=await db.batch(statements);if(!result[0].meta.changes)err('Another update was saved first. Refresh and try again.',409);
}
function currentActor(s,u){const actor=s.users.find(x=>x.id===u.id&&x.active);if(!actor)err('Sign in to save changes.',401);return actor}
function checkVersion(b,s){if(b.version!==undefined&&b.version!==s.version)err('Someone else updated the workspace. Refresh and try again.',409)}
function addAudit(s,u,action){s.audit.unshift({id:crypto.randomUUID(),actorId:u.id,actor:u.name,role:u.role,action,at:new Date().toISOString()})}
async function api(req,env){
 const db=env.DB;if(!db)return json({error:'The workspace database is not configured.'},503);
 const path=new URL(req.url).pathname,write=!['GET','HEAD'].includes(req.method);
 if(write){const origin=req.headers.get('Origin');if(!origin||(origin!==new URL(req.url).origin&&origin!==env.SITE_ORIGIN))err('Cross-origin request denied.',403);if(req.headers.get('X-BIA-Request')!=='1'||!req.headers.get('Content-Type')?.startsWith('application/json'))err('Invalid request.',403);if(Number(req.headers.get('Content-Length'))>20000)err('Request is too large.',413)}
 let user=await userFor(req,db);
 if(path==='/api/state'&&req.method==='GET'){
  const count=await db.prepare('SELECT COUNT(*) AS n FROM users').first();if(!user)return json({user:null,setupRequired:!count.n,demo:true});const s=await readState(db);return json({...visibleState(s,currentActor(s,user)),user:currentActor(s,user),setupRequired:false,demo:false});
 }
 if(!write)err('Not found.',404);
 const reader=req.body?.getReader(),chunks=[];let size=0;if(reader){while(true){const part=await reader.read();if(part.done)break;size+=part.value.byteLength;if(size>20000){await reader.cancel();err('Request is too large.',413)}chunks.push(part.value)}}const bytes=new Uint8Array(size);let offset=0;for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.byteLength}const raw=new TextDecoder().decode(bytes);let b;try{b=JSON.parse(raw)}catch{err('Invalid JSON.',422)}
 if(path==='/api/setup'){
  validateAccount(b);const u={id:crypto.randomUUID(),name:b.name.trim(),email:b.email.toLowerCase().trim(),role:'admin',department:'Digital & IT',active:1};const salt=crypto.randomUUID(),hash=await hashPassword(b.password,salt);
  try{await db.batch([db.prepare('INSERT INTO setup_lock(id) VALUES(1)'),db.prepare('INSERT INTO users(id,email,name,role,department,active,hash,salt) VALUES(?,?,?,?,?,1,?,?)').bind(u.id,u.email,u.name,u.role,u.department,hash,salt)])}catch{err('Administrator setup has already been completed. Sign in instead.',409)}
  await readState(db);return newSession(db,u,req);
 }
 if(path==='/api/login'){
  const email=String(b.email||'').toLowerCase().trim(),key=await sha(email),ipkey=await sha('ip:'+req.headers.get('CF-Connecting-IP'));
  for(const k of [key,ipkey]){const a=await db.prepare('SELECT * FROM attempts WHERE key=?').bind(k).first();if(a&&a.expires>Date.now()&&a.count>=(k===key?8:40))err('Too many attempts. Try again in 15 minutes.',429);await db.prepare('INSERT INTO attempts(key,count,expires) VALUES(?,1,?) ON CONFLICT(key) DO UPDATE SET count=CASE WHEN expires<? THEN 1 ELSE count+1 END, expires=CASE WHEN expires<? THEN excluded.expires ELSE expires END').bind(k,Date.now()+900000,Date.now(),Date.now()).run()}
  const u=await db.prepare('SELECT * FROM users WHERE email=?').bind(email).first();const hashed=await hashPassword(String(b.password||'').slice(0,128),u?.salt||'unavailable-user-salt');let mismatch=0;const expected=u?.hash||'0'.repeat(64);for(let i=0;i<64;i++)mismatch|=hashed.charCodeAt(i)^expected.charCodeAt(i);if(!u||!u.active||mismatch)err('Email or password is incorrect.',401);await db.prepare('DELETE FROM attempts WHERE key=?').bind(key).run();return newSession(db,u,req);
 }
 if(path==='/api/logout'){const token=req.headers.get('Cookie')?.match(/(?:^|;\s*)bia_session=([^;]+)/)?.[1];if(token)await db.prepare('DELETE FROM sessions WHERE token=?').bind(await sha(token)).run();return json({ok:true},200,{'Set-Cookie':'bia_session=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0; Secure'})}
 if(!user)err('Sign in to save changes.',401);
 if(path==='/api/users'){
  validateAccount(b);const s=await readState(db);user=currentActor(s,user);checkVersion(b,s);if(!['admin','head'].includes(user.role))err('Your role cannot manage access.',403);
  if(!Object.hasOwn(roles,b.role)||!allowedChoice(s,'department',b.department))err('Select a valid role and active department.',422);if(user.role==='head'&&(b.role!=='delegate'||b.department!==user.department))err('Vertical heads may create delegates only in their own department.',403);
  if(s.users.some(u=>u.email===b.email.toLowerCase().trim()))err('An account with this email already exists.',409);
  const u={id:crypto.randomUUID(),name:b.name.trim(),email:b.email.toLowerCase().trim(),role:b.role,department:b.department,active:1};const salt=crypto.randomUUID(),hash=await hashPassword(b.password,salt),next=structuredClone(s);
  addAudit(next,user,`Created ${roles[u.role]} account · ${u.name}`);
  await commitState(db,s,next,user,(guard,marker)=>[db.prepare(`INSERT INTO users(id,email,name,role,department,active,hash,salt) SELECT ?,?,?,?,?,1,?,? WHERE ${guard}`).bind(u.id,u.email,u.name,u.role,u.department,hash,salt,marker)]);return json({ok:true});
 }
 if(path==='/api/users/active'){
  const s=await readState(db);user=currentActor(s,user);checkVersion(b,s);const target=s.users.find(u=>u.id===b.id);if(!target)err('Account not found.',404);
  const next=mutate(s,user,'user_edit',{...target,active:b.active});await commitState(db,s,next,user);return json({ok:true});
 }
 if(path==='/api/users/reset-password'){
  const s=await readState(db);user=currentActor(s,user);checkVersion(b,s);if(user.role!=='admin'||b.id===user.id)err('Only an administrator can reset another account’s password.',403);const target=s.users.find(u=>u.id===b.id);if(!target)err('Account not found.',404);validateAccount({...target,password:b.password});
  const salt=crypto.randomUUID(),hash=await hashPassword(b.password,salt),next=structuredClone(s);addAudit(next,user,`Reset password · ${target.name}`);
  await commitState(db,s,next,user,(guard,marker)=>[db.prepare(`UPDATE users SET hash=?,salt=? WHERE id=? AND ${guard}`).bind(hash,salt,b.id,marker),db.prepare(`DELETE FROM sessions WHERE user_id=? AND ${guard}`).bind(b.id,marker)]);return json({ok:true});
 }
 if(path==='/api/password'){
  const u=await db.prepare('SELECT * FROM users WHERE id=?').bind(user.id).first();if(await hashPassword(String(b.current||''),u.salt)!==u.hash)err('Current password is incorrect.',422);validateAccount({...user,password:b.password});const salt=crypto.randomUUID(),hash=await hashPassword(b.password,salt);await db.batch([db.prepare('UPDATE users SET hash=?,salt=? WHERE id=?').bind(hash,salt,user.id),db.prepare('DELETE FROM sessions WHERE user_id=?').bind(user.id)]);return newSession(db,{...u,hash,salt},req);
 }
 if(path==='/api/mutate'){
  const s=await readState(db);user=currentActor(s,user);if(b.version!==s.version)err('Someone else updated the workspace. Refresh and try again.',409);const next=mutate(s,user,b.action,b.payload);
  await commitState(db,s,next,user);return json({ok:true,version:s.version+1,...(b.action==='master'?{masterId:b.payload.id||next.masterProjects.at(-1).id}:{})});
 }
 err('Not found.',404);
}
export default{async fetch(req,env){let response;try{if(new URL(req.url).pathname.startsWith('/api/'))response=await api(req,env);else response=await env.ASSETS.fetch(req)}catch(e){response=json({error:e.status?e.message:'Unable to complete this request. Please try again.'},e.status||500)}const h=new Headers(response.headers);h.set('X-Content-Type-Options','nosniff');h.set('Referrer-Policy','same-origin');h.set('Permissions-Policy','camera=(), microphone=(), geolocation=()');h.set('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'self'");if(new URL(req.url).protocol==='https:')h.set('Strict-Transport-Security','max-age=31536000');return new Response(response.body,{status:response.status,headers:h})}};
