import assert from 'node:assert/strict';
import {JSDOM} from 'jsdom';
import {build} from 'esbuild';
import {Miniflare} from 'miniflare';
import {initializeLocalDatabase} from '../scripts/local-db.mjs';
const mf=new Miniflare({scriptPath:'dist/worker.js',modules:true,compatibilityDate:'2026-05-22',d1Databases:['DB'],cf:false});
await initializeLocalDatabase(mf);
let cookie='',checks=0,delayState=null;
const request=async(path,body)=>{const r=await mf.dispatchFetch('https://bia.test/api/'+path,{method:body?'POST':'GET',headers:{Cookie:cookie,Origin:'https://bia.test','Content-Type':'application/json','X-BIA-Request':'1'},body:body?JSON.stringify(body):undefined});if(r.headers.has('set-cookie'))cookie=r.headers.get('set-cookie').split(';')[0];assert.equal(r.status,200);return r.json()};
await request('setup',{name:'Admin',email:'admin@test.example',password:'Test-password-12345'});
for(const role of ['head','delegate','finance','executive','management'])await request('users',{name:role,email:role+'@test.example',password:'Test-password-12345',role,department:'HR'});
let state=await request('state');const group=state.catalogs.find(c=>c.kind==='department'&&c.name==='HR');
const project=state.projects.find(p=>p.department==='HR');
await request('mutate',{action:'project_access',version:state.version,payload:{id:project.id,accessGroupIds:[group.id]}});
state=await request('state');const task=state.tasks.find(t=>t.projectId===project.id&&!state.tasks.some(c=>c.parentId===t.id));
await request('mutate',{action:'task',version:state.version,payload:{...task,assigneeId:state.users.find(u=>u.role==='delegate').id}});
const adminCookie=cookie;cookie='';
const bundle=await build({entryPoints:['src/main.jsx'],bundle:true,format:'iife',write:false,loader:{'.css':'empty'},define:{'import.meta.env.VITE_EDITION':'"review"'}});
const dom=new JSDOM('<div id="root"></div>',{url:'https://bia.test',runScripts:'outside-only',pretendToBeVisual:true});
const w=dom.window,doc=w.document,errors=[];w.addEventListener('error',e=>errors.push(e.message));
w.fetch=async(path,options={})=>{const r=await mf.dispatchFetch(new URL(path,'https://bia.test'),{...options,headers:{...options.headers,Origin:'https://bia.test',Cookie:cookie}});if(r.headers.has('set-cookie'))cookie=r.headers.get('set-cookie').split(';')[0];if(path==='/api/state'&&delayState){const hold=delayState;delayState=null;await hold;}return r};
const wait=async fn=>{for(let i=0;i<500;i++){if(fn())return;await new Promise(r=>setTimeout(r,10));}throw new Error(doc.body.textContent.slice(-1500))};
const click=text=>{const button=[...doc.querySelectorAll('button')].find(b=>b.textContent.trim()===text);assert(button,text);button.click()};
async function login(role,password='Test-password-12345'){
 await wait(()=>doc.querySelector('form[aria-label="Sign in"]'));const form=doc.querySelector('form');form.elements.email.value=role+'@test.example';form.elements.password.value=password;form.dispatchEvent(new w.SubmitEvent('submit',{bubbles:true,cancelable:true}));
}
async function logout(){doc.querySelector('.profile').click();await wait(()=>doc.querySelector('[role=dialog]'));click('Sign out');await wait(()=>doc.querySelector('.login-page'));assert(!doc.querySelector('.app-shell'));assert(!doc.body.textContent.includes(project.title));checks++;}
try{
 w.eval(bundle.outputFiles[0].text);await wait(()=>doc.querySelector('form'));
 assert(!doc.querySelector('.app-shell'));assert(!doc.body.textContent.includes('StellarKnit'));checks++;
 await login('head','incorrect');await wait(()=>doc.querySelector('[role=alert]'));assert(!doc.querySelector('.app-shell'));assert.equal(doc.querySelector('[name=password]').value,'');checks++;
 for(const role of ['management','head','delegate','finance','executive','admin']){
  await login(role);await wait(()=>doc.querySelector('.app-shell'));
  if(role==='management'){assert(doc.querySelector('.management-dashboard'));assert.equal(doc.querySelectorAll('.management-department-card').length,6);}
  else{assert(doc.querySelector('.kpi-grid'));assert.equal(doc.querySelector('[aria-label="Select master project"]').value,'all');assert.equal(doc.querySelectorAll('.project-row').length,role==='admin'?6:1);}
  const labels=[...doc.querySelectorAll('button')].map(b=>b.textContent.trim());
  assert.equal(labels.includes('Admin portal'),role==='admin');assert.equal(labels.includes('New subproject'),['head','admin'].includes(role));
  if(role==='delegate'||role==='executive'){
   [...doc.querySelectorAll('button')].find(b=>b.textContent.startsWith('Project execution')).click();await wait(()=>doc.querySelector('.task-table'));
   assert.equal([...doc.querySelectorAll('.task-table button')].filter(b=>b.textContent==='Update').length,role==='delegate'?1:0);
   assert([...doc.querySelectorAll('.task-table td')].every(td=>td.hasAttribute('data-label')));
  }
  if(role==='finance'){click('Financial control');await wait(()=>doc.querySelector('.data-table'));assert([...doc.querySelectorAll('button')].some(b=>b.textContent==='New purchase order'));}
  checks++;
  if(role==='admin'){
   // A response begun before logout must never restore the prior user's dashboard.
   let release;delayState=new Promise(resolve=>{release=resolve});doc.querySelector('[aria-label="Refresh workspace"]').click();await new Promise(r=>setTimeout(r,80));await logout();release();await new Promise(r=>setTimeout(r,100));assert(!doc.querySelector('.app-shell'));checks++;
  }else await logout();
 }
 await login('delegate');await wait(()=>doc.querySelector('.app-shell'));
 // Losing a session clears the entire dashboard when the next state check runs.
 cookie='bia_session=expired';doc.querySelector('[aria-label="Refresh workspace"]').click();await wait(()=>doc.querySelector('.login-page'));assert(!doc.querySelector('.app-shell'));checks++;
 assert.deepEqual(errors,[]);console.log(`${checks} authentication UI checks passed: login-first, failed login, all six role landings, role actions, responsive cell labels, logout isolation, delayed response and expired session.`);
}finally{dom.window.close();await mf.dispose();}
