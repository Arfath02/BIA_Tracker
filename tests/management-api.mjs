import assert from 'node:assert/strict';
import {Miniflare} from 'miniflare';
import {initializeLocalDatabase} from '../scripts/local-db.mjs';
const mf=new Miniflare({scriptPath:'dist/worker.js',modules:true,compatibilityDate:'2026-05-22',d1Databases:['DB'],cf:false});await initializeLocalDatabase(mf);let checks=0;
function client(){let cookie='';return async(path,body,expected=200)=>{const r=await mf.dispatchFetch('https://bia.test/api/'+path,{method:body?'POST':'GET',headers:{Origin:'https://bia.test','X-BIA-Request':'1','Content-Type':'application/json',Cookie:cookie},body:body?JSON.stringify(body):undefined});const data=await r.json();assert.equal(r.status,expected,JSON.stringify(data));if(r.headers.get('set-cookie'))cookie=r.headers.get('set-cookie').split(';')[0];checks++;return data}}
const admin=client(),manager=client(),head=client(),executive=client(),password='Management-local-test-password';
try{
 await admin('setup',{name:'Admin',email:'admin@example.test',password});
 for(const [who,name,role] of [[manager,'Manager','management'],[head,'Head','head'],[executive,'Executive','executive']]){await admin('users',{name,email:name.toLowerCase()+'@example.test',role,department:'HR',password});await who('login',{email:name.toLowerCase()+'@example.test',password})}
 const change=async(action,payload)=>admin('mutate',{version:(await admin('state')).version,action,payload});
 const master=await change('master',{title:'Capital programme',owner:'Lead',primaryDepartment:'Engineering'});
 await change('project',{masterId:master.masterId,title:'Management visible empty project',department:'Engineering',owner:'Lead',budget:1000,start:'2026-10-01',due:'2026-12-31'});
 let s=await admin('state'),m=await manager('state');assert.equal(m.projects.length,s.projects.length);assert.equal(m.tasks.length,s.tasks.length);assert.equal(m.masterProjects.length,2);assert.equal(m.pos.length,s.pos.length);assert.equal(m.invoices.length,s.invoices.length);assert.equal(m.updates.length,s.updates.length);assert(!JSON.stringify(m).includes('"hash"'));
 const u=s.users.find(u=>u.role==='management');assert.deepEqual(s.managementGroup.memberIds,[u.id]);assert.equal((await executive('state')).projects.length,0);assert((await head('state')).projects.every(p=>p.department==='HR'));
 for(const action of ['master','project','task','update','po','invoice','payment','catalog','user_edit','project_access'])await manager('mutate',{version:m.version,action,payload:{}},403);
 await manager('users',{name:'Forbidden',email:'forbidden@example.test',role:'admin',department:'HR',password},403);
 await manager('users/active',{id:s.user.id,active:false},403);
 await manager('users/reset-password',{id:s.user.id,password,version:m.version},403);
 await head('users',{name:'Escalated',email:'escalated@example.test',role:'management',department:'HR',password},403);
 await change('user_edit',{...u,role:'executive'});assert.equal((await manager('state')).user,null);
 await manager('login',{email:'manager@example.test',password});assert.equal((await manager('state')).projects.length,0);assert.equal((await admin('state')).managementGroup.memberIds.length,0);
 s=await admin('state');await change('user_edit',{...s.users.find(x=>x.id===u.id),role:'management'});await manager('login',{email:'manager@example.test',password});assert.equal((await manager('state')).projects.length,7);
 await admin('users/active',{id:u.id,active:false});assert.equal((await manager('state')).user,null);await manager('login',{email:'manager@example.test',password},401);
 console.log(`${checks} management API checks passed: full portfolio reads, every mutation denied, admin-only membership, existing role isolation, role-change revocation and disabled accounts.`);
}finally{await mf.dispose()}
