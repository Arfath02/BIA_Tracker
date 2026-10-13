import {catalogRows} from './catalogs.js';
export const DEFAULT_MASTER_ID='bia-digital-transformation';
export const defaultMaster=()=>({id:DEFAULT_MASTER_ID,title:'BIA Digital Transformation',primaryDepartment:'Digital & IT',owner:'Transformation office',description:'Digital transformation programmes and workstreams.'});
// Upgrade v1/v2 snapshots without replacing data or changing record IDs.
export function withMasters(s){
 const primaryDepartment=catalogRows(s).find(d=>d.kind==='department'&&d.id==='department-1')?.name||'Digital & IT';
 const masters=Array.isArray(s.masterProjects)?s.masterProjects:[defaultMaster()];
 return {...s,masterProjects:masters.map(m=>({...m,primaryDepartment:m.primaryDepartment||(m.id===DEFAULT_MASTER_ID?primaryDepartment:null)})),projects:s.projects.map(p=>({...p,masterId:p.masterId||DEFAULT_MASTER_ID}))};
}
export function scopeToMaster(state,masterId){
 const s=withMasters(state);if(masterId==='all')return s;
 const projects=s.projects.filter(p=>p.masterId===masterId),projectIds=new Set(projects.map(p=>p.id));
 const tasks=s.tasks.filter(t=>projectIds.has(t.projectId)),taskIds=new Set(tasks.map(t=>t.id));
 const pos=s.pos.filter(p=>projectIds.has(p.projectId)),poIds=new Set(pos.map(p=>p.id));
 return {...s,projects,tasks,pos,invoices:s.invoices.filter(i=>poIds.has(i.poId)),updates:s.updates.filter(u=>taskIds.has(u.taskId))};
}
