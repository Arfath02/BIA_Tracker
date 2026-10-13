import assert from 'node:assert/strict';
import {Miniflare} from 'miniflare';
import {initializeLocalDatabase} from '../scripts/local-db.mjs';
const mf=new Miniflare({scriptPath:'dist/worker.js',modules:true,compatibilityDate:'2026-05-22',d1Databases:['DB'],cf:false});await initializeLocalDatabase(mf);let checks=0;
function client(){let cookie='';return async(path,body,expected=200)=>{const r=await mf.dispatchFetch('https://bia.test/api/'+path,{method:body?'POST':'GET',headers:{Origin:'https://bia.test','X-BIA-Request':'1','Content-Type':'application/json',Cookie:cookie},body:body?JSON.stringify(body):undefined});const data=await r.json();assert.equal(r.status,expected,JSON.stringify(data));if(r.headers.get('set-cookie'))cookie=r.headers.get('set-cookie').split(';')[0];checks++;return data}}
const admin=client(),head=client(),member=client(),outsider=client(),executive=client(),finance=client(),password='Access-boundary-test-password';
try{
 await admin('setup',{name:'Admin',email:'admin@example.test',password});
 const change=async(who,action,payload,code=200)=>who('mutate',{version:(await who('state')).version,action,payload},code);
 for(const [who,name,role,department] of [[head,'Head','head','HR'],[member,'Member','delegate','HR'],[outsider,'Outsider','delegate','Engineering'],[executive,'Executive','executive','HR'],[finance,'Finance','finance','HR']]){await admin('users',{name,email:name.toLowerCase()+'@example.test',role,department,password});await who('login',{email:name.toLowerCase()+'@example.test',password})}
 let s=await member('state');for(const key of ['masterProjects','projects','tasks','pos','invoices','updates','audit'])assert.equal(s[key].length,0,key);
 s=await head('state');assert(s.projects.length>0);assert(s.projects.every(p=>p.department==='HR'));assert(!s.projects.some(p=>p.id==='erp'));assert(!s.tasks.some(t=>t.projectId==='erp'));assert(!s.pos.some(p=>p.projectId==='erp'));
 await change(head,'project',{masterId:'bia-digital-transformation',title:'HR initiative',department:'HR',owner:'HR lead',budget:1000,start:'2026-09-30',due:'2026-12-31'});
 await change(head,'project',{department:'Engineering'},403);
 s=await admin('state');const account=s.users.find(u=>u.name==='Member'),task=s.tasks.find(t=>t.id==='wf2'),group=s.departmentGroups.find(g=>g.name==='HR');
 await change(head,'task',{...task,assigneeId:account.id});s=await member('state');assert.deepEqual(s.projects.map(p=>p.id),[task.projectId]);assert(s.tasks.every(t=>t.projectId===task.projectId));
 await change(member,'update',{taskId:'erp21',progress:90,blocked:false,note:'Guess hidden task ID'},403);
 await change(admin,'project_access',{id:'erp',accessGroupIds:['invalid']},422);
 s=await admin('state');await change(admin,'project_access',{id:'erp',accessGroupIds:[group.id]});await admin('mutate',{version:s.version,action:'project_access',payload:{id:'erp',accessGroupIds:[]}},409);
 for(const who of [member,executive,finance]){s=await who('state');assert(s.projects.some(p=>p.id==='erp'));assert(s.pos.some(p=>p.projectId==='erp'));assert(s.invoices.length>0);assert(s.tasks.every(t=>s.projects.some(p=>p.id===t.projectId)))}
 assert.equal((await outsider('state')).projects.length,0);
 await change(executive,'project_access',{id:'erp',accessGroupIds:[]},403);
 await change(executive,'update',{taskId:'erp21',progress:90,blocked:false,note:'Read only'},403);
 const po={projectId:'erp',number:'ACCESS-PO',vendor:s.catalogs.find(c=>c.kind==='vendor'&&c.active).name,amount:100,date:'2026-09-30',description:'Authorized shared project'};
 await change(finance,'po',po);await change(finance,'po',{...po,projectId:task.projectId,number:'HIDDEN-PO'},403);
 s=await finance('state');const poId=s.pos.find(p=>p.number==='ACCESS-PO').id;await change(finance,'invoice',{poId,number:'ACCESS-INV',amount:100,date:'2026-09-30',due:'2026-10-30'});
 s=await finance('state');const invoiceId=s.invoices.find(i=>i.number==='ACCESS-INV').id;
 await change(admin,'project_access',{id:'erp',accessGroupIds:[]});
 s=await finance('state');for(const key of ['masterProjects','projects','tasks','pos','invoices','updates'])assert.equal(s[key].length,0,key);assert(!JSON.stringify(s.audit).includes('ACCESS-'));
 await change(finance,'payment',{invoiceId,reference:'Forbidden',paidDate:'2026-09-30'},403);assert.deepEqual((await member('state')).projects.map(p=>p.id),[task.projectId]);
 await change(admin,'project_access',{id:'erp',accessGroupIds:[group.id]});await change(admin,'catalog',{id:group.id,kind:'department',name:'People',active:true});
 assert.equal((await executive('state')).user,null);await executive('login',{email:'executive@example.test',password});s=await executive('state');assert.equal(s.user.department,'People');assert(s.projects.some(p=>p.id==='erp'));
 const executiveAccount=(await admin('state')).users.find(u=>u.role==='executive');await change(admin,'user_edit',{...executiveAccount,department:'Engineering'});await executive('login',{email:'executive@example.test',password});assert.equal((await executive('state')).projects.length,0);
 console.log(`${checks} project-access API checks passed: department membership, creator/head/assignment access, grants, revocation, finance isolation, direct-ID rejection, stale writes and department moves.`);
}finally{await mf.dispose()}
