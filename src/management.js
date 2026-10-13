import {projectVariance,projectCompletion} from './baselines.js';
import {catalogRows} from './catalogs.js';
import {leaves,progress,projectStatus,taskStatus,totals,today} from './domain.js';
export const canViewManagement=user=>!!user&&['admin','management'].includes(user.role);
export function projectReportStatus(s,p){
 const tasks=leaves(s,p.id);if(!tasks.length)return 'Not planned';
 if(tasks.every(t=>t.progress===100))return 'Complete';
 if(projectVariance(s,p).delayed)return 'Delayed';
 if(p.due<today()||tasks.some(t=>t.blocked||t.progress<100&&t.due<today()))return 'At risk';
 return projectStatus(s,p);
}
export function projectScope(s,projects){
 const ids=new Set(projects.map(p=>p.id)),tasks=s.tasks.filter(t=>ids.has(t.projectId)),taskIds=new Set(tasks.map(t=>t.id)),pos=s.pos.filter(p=>ids.has(p.projectId)),poIds=new Set(pos.map(p=>p.id));
 return {...s,projects,tasks,pos,invoices:s.invoices.filter(i=>poIds.has(i.poId)),updates:s.updates.filter(u=>taskIds.has(u.taskId))};
}
export function reportSummary(s,projects=s.projects){
 const scoped=projectScope(s,projects),work=leaves(scoped),statuses=projects.map(p=>projectReportStatus(s,p));
 const complete=statuses.filter(x=>x==='Complete').length,atRisk=statuses.filter(x=>['At risk','Delayed'].includes(x)).length,delayed=projects.filter(p=>projectVariance(s,p).delayed).length,unplanned=statuses.filter(x=>x==='Not planned').length;
 return {progress:progress(scoped),plannedHours:work.reduce((a,t)=>a+t.effort,0),projects:projects.length,tasks:work.length,completedTasks:work.filter(t=>t.progress===100).length,blockedTasks:work.filter(t=>t.blocked&&t.progress<100).length,overdueTasks:work.filter(t=>t.progress<100&&t.due<today()).length,complete,atRisk,delayed,unplanned,early:projects.filter(p=>projectCompletion(s,p).early).length,status:!projects.length?'No projects':delayed?'Delayed':atRisk?'At risk':complete===projects.length?'Complete':unplanned?'Planning needed':'On track',...totals(scoped)};
}
export function departmentReports(s){
 const departments=[...new Set([...catalogRows(s).filter(d=>d.kind==='department'&&(d.active||s.projects.some(p=>p.department===d.name))).map(d=>d.name),...s.projects.map(p=>p.department)])];
 return departments.map(name=>({name,...reportSummary(s,s.projects.filter(p=>p.department===name))}));
}
export function taskTree(s,projectId){
 const rows=[],tasks=s.tasks.filter(t=>t.projectId===projectId),ids=new Set(tasks.map(t=>t.id)),seen=new Set();
 function add(t,depth){if(seen.has(t.id))return;seen.add(t.id);rows.push({...t,depth,summary:tasks.some(x=>x.parentId===t.id),calculatedProgress:progress(s,projectId,t.id),status:taskStatus(s,t)});tasks.filter(c=>c.parentId===t.id).forEach(c=>add(c,depth+1))}
 tasks.filter(t=>!t.parentId||!ids.has(t.parentId)).forEach(t=>add(t,0));return rows;
}
