// Stable master-data IDs; legacy workspaces are hydrated without replacing records.
export const catalogKinds={department:'Departments',vendor:'Vendors',resource:'Resource teams'};
const defaults=['Digital & IT','Warehouse','Production','Quality','HR','Engineering'];
export function catalogRows(s){
 if(Array.isArray(s.catalogs))return s.catalogs;
 const values={department:[...defaults,...(s.masterProjects||[]).map(x=>x.primaryDepartment),...(s.users||[]).map(x=>x.department),...(s.projects||[]).map(x=>x.department)],vendor:(s.pos||[]).map(x=>x.vendor),resource:['Unassigned',...(s.tasks||[]).map(x=>x.resource)]};
 return Object.entries(values).flatMap(([kind,names])=>[...new Set(names.filter(Boolean))].map((name,i)=>({id:`${kind}-${i+1}`,kind,name,active:true})));
}
export const choices=(s,kind,current)=>[...new Set([...catalogRows(s).filter(x=>x.kind===kind&&(x.active||x.name===current)).map(x=>x.name),...(typeof current==='string'&&current?[current]:[])])];
export const allowedChoice=(s,kind,name,current)=>typeof name==='string'&&!!name&&(name===current||choices(s,kind).includes(name));
