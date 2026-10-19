import {withFinance,financeScope,usd,usdMillions,currencyMoney} from './finance.js';
import {commercialActions,commercialMutate,projectCommercial,amountIn,validateInvoiceTerm,validateInvoiceChange} from './commercial.js';
import {calendar,normalizeTask,reschedule,scheduleAudit,effectiveFinish} from './scheduling.js';
import {taskVariance,projectVariance} from './baselines.js';
import {withAccess,canSeeProject,projectForAction} from './access.js';
import {catalogRows,allowedChoice,catalogKinds} from './catalogs.js';
export const departments=['Digital & IT','Warehouse','Production','Quality','HR','Engineering'];
export const roles={admin:'Administrator',management:'Management (read-only)',executive:'Executive',head:'Vertical head',delegate:'Delegate',finance:'Finance'};
export const today=()=>new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Amman',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
export const money=(n,compact=false)=>compact?usdMillions(n):currencyMoney(n);
export const dateLabel=d=>d?new Date(d+'T12:00:00').toLocaleDateString('en-GB',{day:'numeric',month:'short',year:'numeric'}):'—';
export function leaves(s,projectId,parentId){let tasks=s.tasks.filter(t=>!projectId||t.projectId===projectId);if(parentId){const ids=new Set([parentId]);let changed=true;while(changed){changed=false;for(const t of tasks)if(ids.has(t.parentId)&&!ids.has(t.id)){ids.add(t.id);changed=true}}tasks=tasks.filter(t=>ids.has(t.id))}return tasks.filter(t=>!s.tasks.some(x=>x.parentId===t.id))}
export function progress(s,projectId,parentId){let ts=leaves(s,projectId,parentId),weight=ts.reduce((a,t)=>a+t.effort,0);return weight?(ts.every(t=>t.progress===100)?100:Math.min(99,Math.round(ts.reduce((a,t)=>a+t.progress*t.effort,0)/weight))):0}
export function taskStatus(s,t){const p=progress(s,t.projectId,t.id);if(p===100)return 'Complete';if(t.blocked)return 'Blocked';if(taskVariance(s,t).delayed)return 'Delayed';if(t.externalPredecessorsPending||t.predecessors.some(id=>progress(s,null,id)<100))return 'Waiting';if(t.due<today())return 'Overdue';return p?'In progress':'Planned'}
export function projectStatus(s,p){const ts=leaves(s,p.id);if(ts.length&&progress(s,p.id)===100)return 'Complete';if(projectVariance(s,p).delayed)return 'Delayed';if(ts.some(t=>t.blocked||taskStatus(s,t)==='Overdue'))return 'At risk';return 'On track'}
export function canPlan(u,dept){return !!u&&(u.role==='admin'||u.role==='head'&&u.department===dept)}
export function canUpdate(u,t){return canPlan(u,t.department)||!!u&&u.role==='delegate'&&t.assigneeId===u.id}
export function canFinance(u){return !!u&&['admin','finance'].includes(u.role)}
export function totals(s){const project=id=>s.projects.find(p=>p.id===id),invoiceProject=i=>project(s.pos.find(p=>p.id===i.poId)?.projectId);const budget=s.projects.reduce((a,p)=>a+usd(p.budget,p),0),committed=s.pos.reduce((a,p)=>a+usd(p.amount,project(p.projectId)),0),invoiced=s.invoices.reduce((a,i)=>a+usd(i.amount,invoiceProject(i)),0),paid=s.invoices.filter(i=>i.status==='Paid').reduce((a,i)=>a+usd(i.amount,invoiceProject(i)),0);return{budget,committed,invoiced,paid,remaining:budget-committed}}
const fail=m=>{throw Object.assign(new Error(m),{status:422})};
const text=(v,label,max=180)=>{if(typeof v!=='string'||!v.trim()||v.trim().length>max)fail(`${label} is required (maximum ${max} characters).`);return v.trim()};
const num=(v,label,min,max)=>{if(typeof v!=='number'||!Number.isFinite(v)||v<min||v>max)fail(`${label} must be between ${min} and ${max}.`);return v};
const date=(v,label)=>{if(typeof v!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(v)||Number.isNaN(Date.parse(v))||new Date(v).toISOString().slice(0,10)!==v)fail(`${label} must be a valid date.`);return v};
const permission=ok=>{if(!ok)throw Object.assign(new Error('Your role does not allow this action.'),{status:403})};
export function mutate(state,user,action,payload,id=crypto.randomUUID()){
 permission(user?.role!=='management');
 let s=withFinance(withAccess(structuredClone(state))),b=payload||{};s.catalogs=catalogRows(s);let label='';let auditProjectId=projectForAction(s,action,b)?.id||null;
 if(['task','update','po','invoice','payment','project_access','baseline','project_dates','project_calendar',...commercialActions.filter(a=>a!=='consultant')].includes(action))permission(action==='change_decision'&&user.role==='finance'||canSeeProject(s,user,projectForAction(s,action,b)));
 if(commercialActions.includes(action)){const result=commercialMutate(s,user,action,b,id,today());s=result.state;label=result.label;}else if(action==='baseline'){
  const p=s.projects.find(p=>p.id===b.projectId);permission(p&&canPlan(user,p.department));
  const tasks=s.tasks.filter(t=>t.projectId===p.id);if(!tasks.length)fail('Add a task plan before saving a baseline.');
  s.baselines=s.baselines||[];const version=Math.max(0,...s.baselines.filter(x=>x.projectId===p.id).map(x=>x.version))+1;
  const baseline={id,projectId:p.id,version,name:text(b.name,'Baseline name',80),reason:text(b.reason,'Baseline reason',500),createdById:user.id,createdBy:user.name,createdAt:new Date().toISOString(),title:p.title,start:p.start,due:p.due,tasks:tasks.map(t=>({taskId:t.id,parentId:t.parentId,title:t.title,start:t.start,due:t.due,effort:t.effort,isMilestone:!!t.isMilestone}))};
  s.baselines.push(baseline);label=`Saved baseline v${version} · ${p.title} · ${baseline.name}`;
 }else if(action==='project_calendar'){
  const p=s.projects.find(p=>p.id===b.projectId);permission(p&&canPlan(user,p.department));const reason=text(b.reason,'Calendar change reason',300);p.offDays=calendar(b.offDays);
  const changes=reschedule(s,state,[],user,{calendarProject:p.id});label=`Updated working week · ${p.title} · days off ${p.offDays.join(',')||'none'} · ${reason}`+scheduleAudit(changes);
 }else if(action==='project_dates'){
  const p=s.projects.find(p=>p.id===b.projectId);permission(p&&canPlan(user,p.department));const start=date(b.start,'Start'),due=date(b.due,'Due date'),reason=text(b.reason,'Schedule change reason',300);
  if(due<start||s.tasks.some(t=>t.projectId===p.id&&(t.start<start||t.due>due)))fail('Project dates must contain every task.');
  label=`Revised project dates · ${p.start}–${p.due} → ${start}–${due} · ${reason}`;p.start=start;p.due=due;
 }else if(action==='master'){
  permission(user?.role==='admin');const old=b.id?s.masterProjects.find(m=>m.id===b.id):null;if(b.id&&!old)fail('Master project not found.');
  const m={id:old?.id||id,title:text(b.title,'Master project name',100),primaryDepartment:b.primaryDepartment,owner:text(b.owner,'Accountable lead',80),description:typeof b.description==='string'?b.description.trim().slice(0,1000):''};
  if(!allowedChoice(s,'department',m.primaryDepartment,old?.primaryDepartment))fail('Select an active primary department.');
  if(s.masterProjects.some(x=>x.id!==m.id&&x.title.toLowerCase()===m.title.toLowerCase()))fail('A master project with this name already exists.');
  s.masterProjects=old?s.masterProjects.map(x=>x.id===m.id?m:x):[...s.masterProjects,m];label=`${old?'Updated':'Created'} master project · ${m.title}`;
 }else if(action==='project_access'){
  permission(user?.role==='admin');const p=s.projects.find(p=>p.id===b.id);if(!p)fail('Subproject not found.');
  if(!Array.isArray(b.accessGroupIds)||b.accessGroupIds.some(id=>typeof id!=='string'||!s.catalogs.some(g=>g.kind==='department'&&g.id===id)))fail('Select valid department groups.');
  p.accessGroupIds=[...new Set(b.accessGroupIds)];label=`Updated project access · ${p.title}`;
 }else if(action==='catalog'){
  permission(user?.role==='admin');const old=s.catalogs.find(x=>x.id===b.id);if(b.id&&!old)fail('Dropdown value not found.');
  if(!Object.hasOwn(catalogKinds,b.kind)||old&&old.kind!==b.kind)fail('Select a valid dropdown.');
  const name=text(b.name,'Name',b.kind==='department'?60:b.kind==='resource'?80:100);if(typeof b.active!=='boolean')fail('Active must be true or false.');
  if(s.catalogs.some(x=>x.kind===b.kind&&x.id!==old?.id&&x.name.toLowerCase()===name.toLowerCase()))fail('This name already exists in this dropdown.');
  if(b.kind==='department'&&!b.active&&!s.catalogs.some(x=>x.kind==='department'&&x.id!==old?.id&&x.active))fail('Keep at least one active department.');
  if(old&&b.kind==='department'&&name!==old.name){for(const key of ['projects','tasks','users'])for(const row of s[key])if(row.department===old.name)row.department=name;for(const m of s.masterProjects)if(m.primaryDepartment===old.name)m.primaryDepartment=name;}
  if(old&&name!==old.name&&['vendor','resource'].includes(b.kind))for(const row of s[b.kind==='vendor'?'pos':'tasks'])if(row[b.kind]===old.name)row[b.kind]=name;
  const row={id:old?.id||id,kind:b.kind,name,active:b.active};s.catalogs=old?s.catalogs.map(x=>x.id===old.id?row:x):[...s.catalogs,row];
  label=`${old?'Updated':'Added'} ${b.kind} · ${old&&old.name!==name?old.name+' → ':''}${name}${b.active?'':' (inactive)'}`;
 }else if(action==='user_edit'){
  permission(user?.role==='admin');const old=s.users.find(x=>x.id===b.id);if(!old)fail('Account not found.');
  const u={...old,name:text(b.name,'Name',80),email:text(b.email,'Email',254).toLowerCase(),role:b.role,department:b.department,active:b.active};
  if(!/^\S+@\S+\.\S+$/.test(u.email))fail('Enter a valid email address.');if(!Object.hasOwn(roles,u.role)||typeof u.active!=='boolean')fail('Select a valid role and account status.');
  if(!allowedChoice(s,'department',u.department,old.department))fail('Select an active department.');
  if(s.users.some(x=>x.id!==u.id&&x.email.toLowerCase()===u.email))fail('An account with this email already exists.');
  if(u.id===user.id&&(!u.active||u.role!=='admin'))fail('You cannot disable or demote your own administrator account.');
  if(old.active&&old.role==='admin'&&(!u.active||u.role!=='admin')&&!s.users.some(x=>x.id!==u.id&&x.active&&x.role==='admin'))fail('Keep at least one active administrator.');
  if(u.active&&s.tasks.some(t=>t.assigneeId===u.id&&t.progress<100&&!['admin','head','delegate'].includes(u.role)))fail('Reassign this account’s open tasks before changing its role.');
  s.users=s.users.map(x=>x.id===u.id?u:x);label=`Updated account · ${u.name} · ${roles[u.role]} · ${u.active?'active':'disabled'}`;
 }else if(action==='project'){
  permission(user?.role==='admin'||user?.role==='head'&&user.department===b.department);
  const p={id,masterId:b.masterId,createdById:user.id,accessGroupIds:[],offDays:calendar(b.offDays),title:text(b.title,'Project title',100),department:b.department,owner:text(b.owner,'Project lead',80),budget:num(b.budget,'Budget',0,1e10),start:date(b.start,'Start'),due:date(b.due,'Due date'),description:typeof b.description==='string'?b.description.trim().slice(0,1000):'',color:['#b31c3f','#386c77','#ac783d','#6665a8','#537861','#4e6f9d'][s.projects.length%6]};
  if(!s.masterProjects.some(m=>m.id===p.masterId))fail('Select a valid master project.');
  if(!allowedChoice(s,'department',p.department))fail('Select a valid department.');if(p.due<p.start)fail('Due date must follow the start date.');Object.assign(p,projectCommercial(s,b,p,today()));p.budget=amountIn(p.budget,p,'Budget');s.projects.push(p);auditProjectId=p.id;label=`Created subproject · ${p.title}`;
 }else if(action==='task'){
  const project=s.projects.find(p=>p.id===b.projectId);if(!project)fail('Select a valid subproject.');permission(canPlan(user,project.department));
  const old=b.id?s.tasks.find(t=>t.id===b.id):null;if(b.id&&!old)fail('Task not found.');if(old&&old.projectId!==project.id)fail('Tasks cannot move between subprojects.');
  const hiddenPredecessors=(old?.predecessors||[]).filter(pred=>!canSeeProject(s,user,s.projects.find(p=>p.id===s.tasks.find(t=>t.id===pred)?.projectId)));
  const t={id:old?.id||id,projectId:project.id,title:text(b.title,'Task title'),department:project.department,parentId:b.parentId||null,predecessors:Array.isArray(b.predecessors)?[...new Set([...b.predecessors,...hiddenPredecessors])]:hiddenPredecessors,assigneeId:b.assigneeId||null,resource:text(b.resource||old?.resource||'Unassigned','Resource',80),effort:num(b.effort,'Planned hours',1,100000),start:date(b.start,'Start'),due:date(b.due,'Due date'),progress:old?.progress||0,blocked:old?.blocked||false,isMilestone:b.isMilestone===undefined?!!old?.isMilestone:b.isMilestone};
  if(old?.isMilestone&&!t.isMilestone&&s.paymentTerms.some(x=>x.milestoneId===t.id&&!x.cancelled))fail('This milestone is used by a payment condition.');
  if(typeof t.isMilestone!=='boolean')fail('Milestone must be true or false.');
  if(!old||old.start!==t.start||old.due!==t.due)normalizeTask(t,project);
  const dateChanged=old&&(old.start!==t.start||old.due!==t.due);
  const reason=dateChanged&&(s.baselines||[]).some(x=>x.projectId===project.id)?text(b.changeReason,'Schedule change reason',300):'';
  if(!allowedChoice(s,'resource',t.resource,old?.resource))fail('Select an active resource team.');
  if(t.due<t.start)fail('Due date must follow the start date.');if(t.start<project.start)fail('Task start must be within the subproject dates.');
  const parent=t.parentId?s.tasks.find(x=>x.id===t.parentId):null;if(t.parentId&&(!parent||parent.projectId!==t.projectId||parent.id===t.id))fail('Select a valid parent in the same subproject.');
  if(parent&&(parent.progress>0||parent.predecessors.length))fail('Subtasks can be added only to a parent with no recorded progress or predecessors.');
  if(t.assigneeId&&!s.users.some(u=>u.id===t.assigneeId&&u.active&&['head','delegate','admin'].includes(u.role)))fail('Select an active account.');
  for(const pred of t.predecessors){const p=s.tasks.find(x=>x.id===pred);if(!p||pred===t.id)fail('Invalid predecessor.');if(!hiddenPredecessors.includes(pred))permission(canSeeProject(s,user,s.projects.find(x=>x.id===p.projectId)));if(s.projects.find(x=>x.id===p.projectId)?.masterId!==project.masterId)fail('Predecessors must belong to the same master project.');if(effectiveFinish(s,p)>=t.start)fail('Finish-to-start dependencies require the task to start after its predecessor finishes.');}
  s.tasks=old?s.tasks.map(x=>x.id===t.id?t:x):[...s.tasks,t];
  for(const x of s.tasks){if(x.parentId===t.id&&(x.start<t.start||x.due>t.due))fail('Parent dates must contain all subtasks.');}

  const graph=new Map(s.tasks.map(x=>[x.id,[...x.predecessors,...s.tasks.filter(c=>c.parentId===x.id).map(c=>c.id)]]));
  const visited=new Set(),visiting=new Set();function visit(k){if(visiting.has(k))fail('The dependency or parent relationship would create a cycle.');if(visited.has(k))return;visiting.add(k);for(const v of graph.get(k)||[])visit(v);visiting.delete(k);visited.add(k)};for(const t of s.tasks)visit(t.id);
  const changes=dateChanged||!old||JSON.stringify(old.predecessors)!==JSON.stringify(t.predecessors)?reschedule(s,state,[t.id],user):[];
  label=dateChanged?`Revised task dates · ${old.start}–${old.due} → ${t.start}–${t.due}${reason?' · '+reason:''}`:`${old?'Updated':'Created'} task · ${t.title}`;label+=scheduleAudit(changes);
 }else if(action==='update'){
  const t=s.tasks.find(t=>t.id===b.taskId);if(!t)fail('Task not found.');permission(canUpdate(user,t));if(s.tasks.some(x=>x.parentId===t.id))fail('Update the subtasks; summary progress rolls up automatically.');
  const next=num(b.progress,'Progress',0,100),note=text(b.note,'Update note',2000);if(!Number.isInteger(next))fail('Progress must be a whole percentage.');if(typeof b.blocked!=='boolean')fail('Blocked must be true or false.');
  if(next>0&&t.predecessors.some(p=>progress(s,null,p)<100))fail('Complete all predecessors before recording progress.');
  if(next<100&&t.progress===100&&s.tasks.some(x=>x.predecessors.includes(t.id)&&progress(s,x.projectId,x.id)>0))fail('A successor has started; its progress must be revised before reopening this task.');
  if(b.rescheduleSuccessors!==undefined&&typeof b.rescheduleSuccessors!=='boolean')fail('Choose whether to reschedule successors.');
  const early=next===100&&t.progress<100&&today()<t.due;
  if(b.rescheduleSuccessors&&!early)fail('Only newly completed early tasks can bring successors forward.');
  if(early&&b.rescheduleSuccessors)t.progress=next;
  const changes=early&&b.rescheduleSuccessors?reschedule(s,state,[t.id],user,{early:true,completionDay:today()}):[];
  t.progress=next;t.blocked=next===100?false:b.blocked;s.updates.unshift({id,taskId:t.id,progress:next,note,author:user.name,authorId:user.id,createdAt:new Date().toISOString()});label=`Updated progress · ${t.title} → ${next}%`+(early?(b.rescheduleSuccessors?' · Early completion: reschedule confirmed':' · Early completion: retained dates'):'')+scheduleAudit(changes);
 }else if(action==='po'){
  permission(canFinance(user));const p=s.projects.find(p=>p.id===b.projectId);if(!p)fail('Select a valid subproject.');
  const po={id,projectId:p.id,number:text(b.number,'PO number',60),vendor:text(b.vendor,'Vendor',100),amount:num(b.amount,'PO amount',0.0001,1e10),date:date(b.date,'PO date'),description:text(b.description,'Description',300)};
  if(!allowedChoice(s,'vendor',po.vendor))fail('Select an active vendor.');
  po.amount=amountIn(po.amount,p,'PO amount',0.0001);if(s.pos.some(x=>x.number.toLowerCase()===po.number.toLowerCase()))fail('This PO number already exists.');if(s.pos.filter(x=>x.projectId===p.id).reduce((a,x)=>a+x.amount,0)+po.amount>p.budget)fail('This PO exceeds the available subproject budget.');s.pos.push(po);label=`Created PO · ${po.number}`;
 }else if(action==='invoice'){
  permission(canFinance(user));const po=s.pos.find(p=>p.id===b.poId);if(!po)fail('Select a valid purchase order.');
  const inv={id,poId:po.id,number:text(b.number,'Invoice number',60),amount:amountIn(b.amount,s.projects.find(p=>p.id===po.projectId),'Invoice amount',0.0001),date:date(b.date,'Invoice date'),due:date(b.due,'Payment due date'),status:'Unpaid'};
  if(inv.due<inv.date||inv.date<po.date)fail('Check invoice and payment due dates against the PO date.');if(s.invoices.some(x=>x.poId===po.id&&x.number.toLowerCase()===inv.number.toLowerCase()))fail('This invoice number already exists for the PO.');if(s.invoices.filter(x=>x.poId===po.id).reduce((a,x)=>a+x.amount,0)+inv.amount>po.amount+1e-7)fail('Total invoices cannot exceed the purchase order amount.');inv.changeRequestId=validateInvoiceChange(s,b,po,inv.amount);inv.termId=validateInvoiceTerm(s,b,po,inv.amount);s.invoices.push(inv);label=`Recorded invoice · ${inv.number}`;
 }else if(action==='payment'){
  permission(canFinance(user));const i=s.invoices.find(x=>x.id===b.invoiceId);if(!i)fail('Invoice not found.');if(i.status==='Paid')fail('This invoice is already paid.');i.reference=text(b.reference,'Payment reference',100);i.paidDate=date(b.paidDate,'Payment date');if(i.paidDate<i.date||i.paidDate>today())fail('Payment date must be between the invoice date and today.');i.status='Paid';label=`Recorded payment · ${i.number}`;
 }else fail('Unknown action.');
 for(const t of s.tasks){const old=state.tasks.find(x=>x.id===t.id);if(old&&(old.start!==t.start||old.due!==t.due))s.audit.unshift({id:crypto.randomUUID(),projectId:t.projectId,actorId:user.id,actor:user.name,role:user.role,action:`Schedule · ${t.title} · ${old.start}–${old.due} → ${t.start}–${t.due}`,at:new Date().toISOString()});}
 s.audit.unshift({id,projectId:auditProjectId,actorId:user.id,actor:user.name,role:user.role,action:label,at:new Date().toISOString()});s.audit=s.audit.slice(0,1000);return s;
}
