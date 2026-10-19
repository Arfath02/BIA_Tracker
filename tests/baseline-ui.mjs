import assert from 'node:assert/strict';
import {JSDOM} from 'jsdom';
import {build} from 'esbuild';
import {Miniflare} from 'miniflare';
import {initializeLocalDatabase} from '../scripts/local-db.mjs';
const mf=new Miniflare({scriptPath:'dist/worker.js',modules:true,compatibilityDate:'2026-05-22',d1Databases:['DB'],cf:false});await initializeLocalDatabase(mf);
let cookie='',checks=0;
const api=async(path,body,status=200)=>{const r=await mf.dispatchFetch('https://bia.test/api/'+path,{method:body?'POST':'GET',headers:{Cookie:cookie,Origin:'https://bia.test','Content-Type':'application/json','X-BIA-Request':'1'},body:body?JSON.stringify(body):undefined});if(r.headers.has('set-cookie'))cookie=r.headers.get('set-cookie').split(';')[0];assert.equal(r.status,status,await r.clone().text());return r.json()};
await api('setup',{name:'Admin',email:'admin@test.example',password:'Test-password-12345'});
let s=await api('state');await api('mutate',{action:'project',version:s.version,payload:{masterId:'bia-digital-transformation',title:'Baseline UI Project',department:'Digital & IT',owner:'Lead',budget:1000,start:'2080-01-01',due:'2080-12-31'}});
s=await api('state');const project=s.projects.find(p=>p.title==='Baseline UI Project');await api('mutate',{action:'task',version:s.version,payload:{projectId:project.id,title:'Milestone UI Go Live',resource:'Unassigned',effort:10,start:'2080-02-01',due:'2080-02-10',predecessors:[],isMilestone:true}});
const bundle=await build({entryPoints:['src/main.jsx'],bundle:true,format:'iife',write:false,loader:{'.css':'empty'},define:{'import.meta.env.VITE_EDITION':'"review"'}});
const dom=new JSDOM('<div id="root"></div>',{url:'https://bia.test',runScripts:'outside-only',pretendToBeVisual:true}),w=dom.window,doc=w.document,errors=[];
w.addEventListener('error',e=>errors.push(e.message));w.fetch=async(path,options={})=>{const r=await mf.dispatchFetch(new URL(path,'https://bia.test'),{...options,headers:{...options.headers,Origin:'https://bia.test',Cookie:cookie}});if(r.headers.has('set-cookie'))cookie=r.headers.get('set-cookie').split(';')[0];return r};
const wait=async fn=>{for(let i=0;i<400;i++){if(fn())return;await new Promise(r=>setTimeout(r,10))}throw Error(doc.body.textContent.slice(-3000))};
const top=()=>[...doc.querySelectorAll('[role=dialog]')].at(-1);
const click=(text,scope=doc)=>{const b=[...scope.querySelectorAll('button')].find(b=>b.textContent.trim()===text);assert(b,text);b.click()};
const set=(el,value)=>{const proto=el.tagName==='SELECT'?w.HTMLSelectElement.prototype:el.tagName==='TEXTAREA'?w.HTMLTextAreaElement.prototype:w.HTMLInputElement.prototype;Object.getOwnPropertyDescriptor(proto,'value').set.call(el,value);el.dispatchEvent(new w.Event('input',{bubbles:true}));el.dispatchEvent(new w.Event('change',{bubbles:true}))};
const fill=(name,value)=>set(top().querySelector(`[name="${name}"]`),value);
const submit=()=>top().querySelector('form').dispatchEvent(new w.SubmitEvent('submit',{bubbles:true,cancelable:true}));
try{
 w.eval(bundle.outputFiles[0].text);await wait(()=>doc.querySelector('.project-row'));
 [...doc.querySelectorAll('.project-row')].find(b=>b.textContent.includes(project.title)).click();await wait(()=>top()?.querySelector('.baseline-panel'));
 click('Save baseline',top());await wait(()=>top()?.querySelector('[name=name]'));fill('name','Original approved');fill('reason','Approved by owner');submit();await wait(()=>top()?.querySelector('.baseline-panel select'));assert(top().textContent.includes('v1'));checks++;
 click('◆ Milestone UI Go Live',top());await wait(()=>top()?.querySelector('[name=changeReason]'));fill('due','2080-02-20');submit();await wait(()=>top()?.textContent.includes('Schedule change reason is required'));checks++;
 fill('changeReason','Delivery deferred');submit();await wait(()=>top()?.textContent.includes('Confirm task date change'));click('Confirm date change',top());await wait(()=>top()?.querySelector('.baseline-panel'));assert(top().textContent.includes('Delayed 10d'));assert(top().textContent.includes('2080-02-10'));checks++;
 click('Timeline',top());await wait(()=>top()?.querySelector('.gantt-baseline'));assert(top().querySelector('.gantt-bar.late'));assert(top().querySelector('.gantt-milestone'));assert(top().querySelector('.gantt-baseline[title="Baseline: 2080-02-01 to 2080-02-10"]'));assert([...top().querySelectorAll('.gantt-bar')].some(b=>b.title.includes('2080-02-01 to 2080-02-20')));checks++;
 click('Breakdown',top());await wait(()=>top()?.querySelector('.breakdown-row'));assert(top().querySelector('.breakdown-row.schedule-delayed'));checks++;
 click('Save new baseline',top());await wait(()=>top()?.querySelector('[name=name]'));fill('name','Revision approved');fill('reason','Change approved');submit();await wait(()=>top()?.querySelector('.baseline-panel select')?.options.length===2);const select=top().querySelector('.baseline-panel select');assert(select.selectedOptions[0].textContent.includes('v1'));set(select,select.options[1].value);await wait(()=>top()?.querySelector('.baseline-heading').textContent.includes('On baseline'));checks++;
 set(select,select.options[0].value);await wait(()=>top()?.querySelector('.baseline-heading').textContent.includes('Delayed 10d'));
 click('Revise project dates',top());await wait(()=>top()?.querySelector('[name=reason]'));fill('due','2081-01-10');fill('reason','Extend project deadline');submit();await wait(()=>top()?.querySelector('.baseline-panel'));assert(top().querySelector('.baseline-metrics').textContent.includes('2080-12-31'));assert(top().querySelector('.baseline-metrics').textContent.includes('2081-01-10'));checks++;
 top().querySelector('[aria-label="Close dialog"]').click();click('Management dashboard');await wait(()=>doc.querySelector('.management-dashboard'));doc.querySelector('[aria-label="Open department Digital & IT"]').click();await wait(()=>doc.querySelector('.management-projects'));click(project.title);await wait(()=>doc.querySelector('.management-project-detail'));assert(doc.querySelector('.management-project-detail').textContent.includes('Delayed 10d'));assert(doc.querySelector('.schedule-current.late'));assert(doc.querySelector('.breakdown-row.schedule-delayed'));assert(!doc.querySelector('.baseline-actions'));checks++;
 // Verify persisted immutable versions via a new API read, not only DOM state.
 s=await api('state');const bs=s.baselines.filter(b=>b.projectId===project.id);assert.equal(bs.length,2);assert.equal(bs[0].tasks[0].due,'2080-02-10');assert.equal(bs[1].tasks[0].due,'2080-02-20');assert(s.tasks.find(t=>t.projectId===project.id).isMilestone);checks++;
 const stale=s.version;await api('mutate',{action:'baseline',version:stale,payload:{projectId:project.id,name:'Third',reason:'New approval'}});await api('mutate',{action:'baseline',version:stale,payload:{projectId:project.id,name:'Concurrent',reason:'Rejected'}},409);checks++;
 assert.deepEqual(errors,[]);console.log(`${checks} baseline UI/API checks passed: capture, reason validation, revised milestone, original/current timeline, breakdown, versions, project dates, management read-only views, persisted snapshots and stale capture.`);
}finally{dom.window.close();await mf.dispose()}
