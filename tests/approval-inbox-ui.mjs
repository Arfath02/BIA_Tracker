import assert from 'node:assert/strict';
import {JSDOM} from 'jsdom';
import {build} from 'esbuild';
import {Miniflare} from 'miniflare';
import {initializeLocalDatabase} from '../scripts/local-db.mjs';
const mf=new Miniflare({scriptPath:'dist/worker.js',modules:true,compatibilityDate:'2026-05-22',d1Databases:['DB'],cf:false});await initializeLocalDatabase(mf);
let cookie='',checks=0;
const api=async(path,body,status=200)=>{const r=await mf.dispatchFetch('https://bia.test/api/'+path,{method:body?'POST':'GET',headers:{Cookie:cookie,Origin:'https://bia.test','Content-Type':'application/json','X-BIA-Request':'1'},body:body?JSON.stringify(body):undefined});if(r.headers.has('set-cookie'))cookie=r.headers.get('set-cookie').split(';')[0];assert.equal(r.status,status,await r.clone().text());return r.json()};
await api('setup',{name:'Admin',email:'admin@test.example',password:'Test-password-12345'});
let s=await api('state');
const project=s.projects[0],originalBudget=project.budget;
await api('mutate',{action:'change_request',version:s.version,payload:{projectId:project.id,title:'Integration extension',reason:'Additional supplier interface',amount:5000}});
await api('users',{name:'Approver',email:'approver@test.example',password:'Test-password-12345',role:'finance',department:'HR'});
await api('login',{email:'approver@test.example',password:'Test-password-12345'});s=await api('state');

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
 w.eval(bundle.outputFiles[0].text);await wait(()=>doc.querySelector('.approval-notice'));
 assert.equal(s.projects.length,0);assert(s.approvalInbox.some(x=>x.project.id===project.id));
 click('Open approval inbox');await wait(()=>doc.querySelector('[aria-label="Finance approval inbox"]'));click('Review request');await wait(()=>top()?.querySelector('[name=decisionNote]'));fill('decisionNote','Central finance reviewed');click('Approve budget change',top());await wait(()=>!top());s=await api('state');assert.equal(s.approvalInbox[0].request.status,'Approved');assert.equal(s.projects.length,0);assert.equal(s.tasks.length,0);assert.equal(s.approvalInbox[0].project.budget,originalBudget+5000);assert(!doc.querySelector('.approval-notice'));assert.deepEqual(errors,[]);console.log('Central finance inbox approval passed without granting task/project visibility.');
}finally{dom.window.close();await mf.dispose()}
