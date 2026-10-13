import {initializeLocalDatabase} from '../scripts/local-db.mjs';
import assert from 'node:assert/strict';
import {Miniflare} from 'miniflare';
const mf=new Miniflare({scriptPath:'dist/worker.js',modules:true,compatibilityDate:'2026-05-22',d1Databases:['DB'],cf:false});
await initializeLocalDatabase(mf);
let checks=0;
function client(){let cookie='';return async(path,body,expected=200)=>{const r=await mf.dispatchFetch('https://bia.test/api/'+path,{method:body?'POST':'GET',headers:{Origin:'https://bia.test','X-BIA-Request':'1','Content-Type':'application/json',Cookie:cookie},body:body?JSON.stringify(body):undefined});const data=await r.json();assert.equal(r.status,expected,JSON.stringify(data));if(r.headers.get('set-cookie'))cookie=r.headers.get('set-cookie').split(';')[0];checks++;return data}}
const admin=client(),head=client();const password='Test-only-password-239!';
try{
 await admin('setup',{name:'Admin',email:'admin@example.test',password});let s=await admin('state');
 await admin('users',{name:'Head',email:'head@example.test',password,role:'head',department:'HR',version:s.version});await head('login',{email:'head@example.test',password});
 const change=async(action,payload,code=200)=>{s=await admin('state');return admin('mutate',{version:s.version,action,payload},code)};
 await head('mutate',{version:(await head('state')).version,action:'catalog',payload:{kind:'department',name:'Forbidden',active:true}},403);
 await change('catalog',{kind:'department',name:'Sales',active:true});s=await admin('state');assert(s.catalogs.some(x=>x.name==='Sales'));
 await change('catalog',{kind:'department',name:'sAlEs',active:true},422);
 const hr=s.catalogs.find(x=>x.name==='HR');await change('catalog',{...hr,name:'People & Culture'});
 s=await admin('state');assert(s.projects.some(x=>x.department==='People & Culture'));assert(!s.tasks.some(x=>x.department==='HR'));assert.equal(s.users.find(x=>x.email==='head@example.test').department,'People & Culture');
 assert.equal((await head('state')).user,null);await head('login',{email:'head@example.test',password});assert.equal((await head('state')).user.department,'People & Culture');
 await admin('users',{name:'New delegate',email:'new@example.test',password,role:'delegate',department:'People & Culture',version:s.version});
 await admin('users',{name:'Stale delegate',email:'stale@example.test',password,role:'delegate',department:'People & Culture',version:s.version},409);
 await change('catalog',{...hr,name:'People & Culture',active:false});await admin('users',{name:'Inactive dept',email:'inactive@example.test',password,role:'delegate',department:'People & Culture'},422);
 s=await admin('state');let target=s.users.find(x=>x.email==='new@example.test');await change('user_edit',{...target,name:'Renamed delegate'});assert((await admin('state')).users.some(x=>x.name==='Renamed delegate'));
 await change('user_edit',{...s.user,active:false},422);await change('user_edit',{...s.user,role:'executive'},422);
 const headUser=(await admin('state')).users.find(x=>x.email==='head@example.test');await change('user_edit',{...headUser,role:'executive'});assert.equal((await head('state')).user,null);
 await head('login',{email:'head@example.test',password});s=await admin('state');await admin('users/reset-password',{id:headUser.id,password:'Replacement-test-password!',version:s.version});assert.equal((await head('state')).user,null);await head('login',{email:'head@example.test',password},401);await head('login',{email:'head@example.test',password:'Replacement-test-password!'});
 const vendor=(await admin('state')).catalogs.find(x=>x.kind==='vendor');await change('catalog',{...vendor,active:false});await change('po',{projectId:'erp',number:'INACTIVE-PO',vendor:vendor.name,amount:1,date:'2026-09-29',description:'Must reject'},422);
 // Both snapshots race with the same version. No losing rename may affect users.
 s=await admin('state');const dept=s.catalogs.find(x=>x.name==='Digital & IT');
 const db=await mf.getD1Database('DB');
 const req=async name=>{const a=client();await a('login',{email:'admin@example.test',password});return a};
 const [a,b]=await Promise.all([req(),req()]);
 // Use direct calls so either competing operation can be the expected winner.
 const versions=await Promise.allSettled([a('mutate',{version:s.version,action:'catalog',payload:{...dept,name:'Technology A'}}),b('mutate',{version:s.version,action:'catalog',payload:{...dept,name:'Technology B'}})]);
 assert.equal(versions.filter(x=>x.status==='fulfilled').length,1);assert.match(versions.find(x=>x.status==='rejected').reason.message,/409/);
 const final=await admin('state');const winner=final.catalogs.find(x=>x.id===dept.id).name;assert.equal(final.users.find(x=>x.email==='admin@example.test').department,winner);assert(final.projects.filter(x=>x.id==='erp').every(x=>x.department===winner));
 assert(final.audit.some(x=>x.action.startsWith('Reset password')));assert(!JSON.stringify(final).includes('Replacement-test-password'));
 console.log(`${checks} admin API checks passed: master data, rename cascades, role restrictions, inactive choices, stale writes, account editing, password resets, session revocation and atomic competing renames.`);
}finally{await mf.dispose()}
