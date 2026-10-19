import {withFinance,financeScope} from './finance.js';
import {withMasters} from './masters.js';
import {catalogRows} from './catalogs.js';
export function withAccess(state){const s=withFinance(withMasters(state));return {...s,projects:s.projects.map(p=>({...p,createdById:p.createdById||null,accessGroupIds:p.accessGroupIds||[]}))}}
export const departmentGroups=s=>catalogRows(s).filter(x=>x.kind==='department').map(d=>({id:d.id,name:d.name,active:d.active,memberIds:s.users.filter(u=>u.active&&u.department===d.name).map(u=>u.id)}));
export function canSeeProject(s,u,p){
 if(!u||!p)return false;if(['admin','management'].includes(u.role))return true;
 if(p.createdById===u.id||u.role==='head'&&p.department===u.department)return true;
 if(s.tasks.some(t=>t.projectId===p.id&&t.assigneeId===u.id))return true;
 const group=catalogRows(s).find(g=>g.kind==='department'&&g.name===u.department);
 return !!group&&(p.accessGroupIds||[]).includes(group.id);
}
export function projectForAction(s,action,b){
 if(['task','po','baseline','project_dates','project_calendar','project_commercial','payment_term','consultant','trip','expense','change_request','change_decision'].includes(action))return s.projects.find(p=>p.id===b.projectId);
 if(action==='project_access')return s.projects.find(p=>p.id===b.id);
 const task=action==='update'?s.tasks.find(t=>t.id===b.taskId):null;
 const invoice=action==='payment'?s.invoices.find(i=>i.id===b.invoiceId):null;
 const po=action==='invoice'?s.pos.find(p=>p.id===b.poId):invoice?s.pos.find(p=>p.id===invoice.poId):null;
 return s.projects.find(p=>p.id===(task?.projectId||po?.projectId));
}
function completed(s,id){const children=s.tasks.filter(t=>t.parentId===id);return children.length?children.every(t=>completed(s,t.id)):s.tasks.some(t=>t.id===id&&t.progress===100)}
// The API returns only authorized records; browser filters are not access control.
export function visibleState(state,user){
 const s=withAccess(state),groups=departmentGroups(s);s.approvalInbox=['admin','finance'].includes(user.role)?s.changeRequests.map(c=>({request:c,project:Object.fromEntries(['id','title','department','currency','budget'].map(k=>[k,s.projects.find(p=>p.id===c.projectId)?.[k]]))})):[];
 if(user.role==='admin')return {...s,departmentGroups:groups,managementGroup:{id:'management',name:'Management',memberIds:s.users.filter(u=>u.active&&u.role==='management').map(u=>u.id)}};
 const projects=s.projects.filter(p=>canSeeProject(s,user,p)),projectIds=new Set(projects.map(p=>p.id)),masterIds=new Set(projects.map(p=>p.masterId));
 const tasks=s.tasks.filter(t=>projectIds.has(t.projectId)),taskIds=new Set(tasks.map(t=>t.id)),pos=s.pos.filter(p=>projectIds.has(p.projectId)),poIds=new Set(pos.map(p=>p.id));
 const memberIds=new Set([user.id,...projects.map(p=>p.createdById),...tasks.map(t=>t.assigneeId)]);
 return {...s,...financeScope(s,projects),baselines:(s.baselines||[]).filter(b=>projectIds.has(b.projectId)),masterProjects:s.masterProjects.filter(m=>user.role==='management'||masterIds.has(m.id)),projects,tasks:tasks.map(t=>({...t,predecessors:t.predecessors.filter(id=>taskIds.has(id)),externalPredecessorCount:t.predecessors.filter(id=>!taskIds.has(id)).length,externalPredecessorsPending:t.predecessors.filter(id=>!taskIds.has(id)&&!completed(s,id)).length})),pos,invoices:s.invoices.filter(i=>poIds.has(i.poId)),updates:s.updates.filter(u=>taskIds.has(u.taskId)),audit:s.audit.filter(a=>projectIds.has(a.projectId)||!a.projectId&&a.actorId===user.id),users:s.users.filter(u=>memberIds.has(u.id)||['admin','head'].includes(user.role)||u.role==='admin'||user.role==='head'&&u.department===user.department),departmentGroups:groups.filter(g=>g.name===user.department).map(g=>({...g,memberIds:g.memberIds.filter(id=>memberIds.has(id))}))};
}
