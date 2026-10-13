import test from 'node:test';
import assert from 'node:assert/strict';
import {seed} from '../src/seed.js';
import {mutate,projectStatus,taskStatus} from '../src/domain.js';
import {baselineFor,taskVariance,projectVariance,baselineProgress} from '../src/baselines.js';
import {visibleState} from '../src/access.js';
import {departmentReports} from '../src/management.js';
const admin={id:'admin',name:'Admin',role:'admin',department:'Digital & IT',active:true};
function fixture(){const s=seed();s.users=[admin];s.projects=[{...s.projects[0],id:'p',start:'2080-01-01',due:'2080-12-31'}];s.tasks=[{id:'t',projectId:'p',title:'Go live',department:s.projects[0].department,parentId:null,predecessors:[],assigneeId:null,resource:'Unassigned',effort:10,start:'2080-02-01',due:'2080-02-10',progress:0,blocked:false,isMilestone:true}];s.pos=[];s.invoices=[];s.updates=[];s.audit=[];return mutate(s,admin,'baseline',{projectId:'p',name:'Approved',reason:'Agreed plan'},'b1')}
test('baseline dates stay immutable after revision; later dates roll up immediately',()=>{const s=fixture(),copy=structuredClone(s.baselines[0]);const next=mutate(s,admin,'task',{...s.tasks[0],due:'2080-02-20',changeReason:'Supplier delay'});assert.deepEqual(next.baselines[0],copy);assert.equal(taskVariance(next,next.tasks[0]).delayDays,10);assert.equal(taskStatus(next,next.tasks[0]),'Delayed');assert.equal(projectStatus(next,next.projects[0]),'Delayed');assert.equal(departmentReports(next).find(d=>d.name===next.projects[0].department).status,'Delayed');assert.throws(()=>mutate(s,admin,'task',{...s.tasks[0],due:'2080-02-20'}),/reason/);});
test('saved versions append and original remains default; comparison can select a later version',()=>{let s=fixture();s=mutate(s,admin,'task',{...s.tasks[0],due:'2080-02-20',changeReason:'Change'});s=mutate(s,admin,'baseline',{projectId:'p',name:'Revised',reason:'Approved revision'},'b2');assert.equal(s.baselines.length,2);assert.equal(baselineFor(s,'p').version,1);assert.equal(projectVariance(s,s.projects[0]).delayDays,10);assert.equal(taskVariance({...s,baselineChoices:{p:'b2'}},s.tasks[0]).delayDays,0);});
test('baseline access and snapshot visibility follow project authorization',()=>{const s=fixture();for(const role of ['delegate','executive','finance','management'])assert.throws(()=>mutate(s,{...admin,role},'baseline',{projectId:'p',name:'Bad',reason:'Bad'}),e=>e.status===403);assert.throws(()=>mutate(s,{...admin,role:'head',department:'HR'},'baseline',{projectId:'p',name:'Bad',reason:'Bad'}),e=>e.status===403);assert.equal(visibleState(s,{...admin,id:'other',role:'delegate',department:'HR'}).baselines.length,0);assert.equal(visibleState(s,{...admin,role:'management'}).baselines.length,1);});
test('overdue original target remains delayed even without a revised date; completed lateness persists',()=>{const s=fixture(),t=s.tasks[0];assert.equal(taskVariance(s,t,'2080-02-15').delayDays,5);t.progress=100;s.updates=[{taskId:'t',progress:100,createdAt:'2080-02-12T12:00:00Z'}];assert.equal(taskVariance(s,t,'2080-03-01').delayDays,2);assert.equal(taskStatus(s,t),'Complete');});
test('new tasks are explicitly unbaselined; milestone planned progress jumps at target',()=>{const s=fixture();s.tasks.push({...s.tasks[0],id:'new'});assert.equal(taskVariance(s,s.tasks[1]).label,'Added after baseline');assert.equal(baselineProgress(s,s.projects[0],'2080-02-09').planned,0);assert.equal(baselineProgress(s,s.projects[0],'2080-02-10').planned,100);});
test('project schedule revisions require reasons, preserve task containment and original dates',()=>{const s=fixture();const next=mutate(s,admin,'project_dates',{projectId:'p',start:'2080-01-01',due:'2081-01-10',reason:'Approved extension'});assert.equal(projectVariance(next,next.projects[0]).delayDays,10);assert.equal(next.baselines[0].due,'2080-12-31');assert.throws(()=>mutate(s,admin,'project_dates',{projectId:'p',start:'2080-02-05',due:'2080-12-31',reason:'Invalid'}),/contain/);});

test('early completion uses final leaf completion and original baseline, never a forecast or missing history',async()=>{
 const {projectCompletion}=await import('../src/baselines.js');const s=fixture(),p=s.projects[0],t=s.tasks[0];
 assert.equal(projectCompletion(s,p).early,false);
 t.progress=100;assert.equal(projectCompletion(s,p).early,false);
 s.updates=[{taskId:t.id,progress:100,createdAt:'2080-12-20T12:00:00Z'}];
 assert.equal(projectCompletion(s,p).earlyDays,11);assert.equal(projectCompletion(s,p).basis,'original baseline');
 p.due='2081-02-01';assert.equal(projectCompletion(s,p).earlyDays,11);assert.equal(projectVariance(s,p).delayed,false);
 s.tasks.push({...t,id:'second',progress:99});assert.equal(projectCompletion(s,p).early,false);
 s.tasks[1].progress=100;s.updates.push({taskId:'second',progress:100,createdAt:'2080-12-30T12:00:00Z'});assert.equal(projectCompletion(s,p).earlyDays,1);
 s.tasks[1].progress=0;assert.equal(projectCompletion(s,p).early,false);
});
test('unbaselined completion labels its comparison and department totals count early delivery',async()=>{
 const {projectCompletion}=await import('../src/baselines.js');const s=fixture();s.baselines=[];s.tasks[0].progress=100;s.updates=[{taskId:'t',progress:100,createdAt:'2080-12-20T12:00:00Z'}];
 assert.equal(projectCompletion(s,s.projects[0]).basis,'current plan (no baseline)');assert.equal(departmentReports(s).find(d=>d.name===s.projects[0].department).early,1);
});
