import assert from 'node:assert/strict';
import {Miniflare} from 'miniflare';
import {initializeLocalDatabase} from '../scripts/local-db.mjs';
import {seed} from '../src/seed.js';
const mf=new Miniflare({scriptPath:'dist/worker.js',modules:true,compatibilityDate:'2026-05-22',d1Databases:['DB'],cf:false});
await initializeLocalDatabase(mf);let checks=0;
function client(){let cookie='';return async(path,body,expected=200)=>{const r=await mf.dispatchFetch('https://bia.test/api/'+path,{method:body?'POST':'GET',headers:{Origin:'https://bia.test','X-BIA-Request':'1','Content-Type':'application/json',Cookie:cookie},body:body?JSON.stringify(body):undefined});const data=await r.json();assert.equal(r.status,expected,JSON.stringify(data));if(r.headers.get('set-cookie'))cookie=r.headers.get('set-cookie').split(';')[0];checks++;return data}}
const admin=client(),head=client(),password='Isolated-master-test-password';
try{
 // Start with a genuine v2 JSON record lacking masterProjects/masterId.
 const db=await mf.getD1Database('DB');await db.prepare('INSERT INTO workspace(id,version,data) VALUES(1,1,?)').bind(JSON.stringify(seed())).run();
 await admin('setup',{name:'Admin',email:'admin@example.test',password});let s=await admin('state');assert.equal(s.masterProjects[0].title,'BIA Digital Transformation');assert(s.projects.every(p=>p.masterId==='bia-digital-transformation'));
 const change=async(action,payload,code=200)=>admin('mutate',{version:(await admin('state')).version,action,payload},code);
 await change('master',{title:'Missing department',owner:'Lead'},422);await change('master',{title:'Invalid department',owner:'Lead',primaryDepartment:'Unknown'},422);
 const result=await change('master',{title:'Factory expansion',owner:'Engineering',primaryDepartment:'Engineering',description:'Capital works'});assert(result.masterId);const id=result.masterId;
 await change('project',{masterId:id,title:'Civil works',department:'Engineering',owner:'Lead',budget:10000,start:'2026-09-30',due:'2026-12-31'});
 s=await admin('state');assert.equal(s.projects.find(p=>p.title==='Civil works').masterId,id);const previous=s.version;
 await change('master',{id,title:'Plant expansion',owner:'Engineering',primaryDepartment:'Engineering',description:'Capital works'});
 await admin('mutate',{version:previous,action:'master',payload:{title:'Stale',owner:'Lead'}},409);
 await change('master',{title:'PLANT EXPANSION',owner:'Lead',primaryDepartment:'Engineering'},422);
 await change('project',{masterId:'invalid',title:'Invalid master',department:'Engineering',owner:'Lead',budget:100,start:'2026-09-30',due:'2026-12-31'},422);
 await admin('users',{name:'Head',email:'head@example.test',password,role:'head',department:'Engineering'});await head('login',{email:'head@example.test',password});s=await head('state');
 await head('mutate',{version:s.version,action:'master',payload:{title:'Unauthorized',owner:'Head'}},403);
 const task={projectId:s.projects.find(p=>p.title==='Civil works').id,title:'Foundation',resource:'Unassigned',effort:20,start:'2026-09-30',due:'2026-10-30',predecessors:['wf1']};await head('mutate',{version:s.version,action:'task',payload:task},403);await head('mutate',{version:s.version,action:'task',payload:{...task,predecessors:[]}});
 s=await admin('state');assert.equal(s.masterProjects.find(m=>m.id===id).primaryDepartment,'Engineering');assert.equal(s.masterProjects.length,2);assert.equal(s.projects.length,7);assert.equal(s.tasks.length,seed().tasks.length+1);
 const stored=JSON.parse((await db.prepare('SELECT data FROM workspace WHERE id=1').first()).data);assert.equal(stored.masterProjects.length,2);assert(stored.projects.every(p=>p.masterId));
 const anonymous=await client()('state');assert.deepEqual(anonymous,{user:null,setupRequired:false,demo:true});
 console.log(`${checks} multi-master API checks passed: legacy upgrade, persisted hierarchy, rename, duplicate/invalid/stale rejection, RBAC and predecessor isolation.`);
}finally{await mf.dispose()}
