// ISO dates and weekday numbers: Sunday=0 ... Saturday=6. No implicit weekend.
const fail=m=>{throw Object.assign(new Error(m),{status:422})};
export const weekdays=['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];
export function calendar(v=[]){if(!Array.isArray(v)||v.some(n=>!Number.isInteger(n)||n<0||n>6)||new Set(v).size!==v.length||v.length===7)fail('Choose weekly days off, leaving at least one working day.');return [...v].sort();}
export function plus(d,n=1){const x=new Date(d+'T12:00:00Z');x.setUTCDate(x.getUTCDate()+n);const out=x.toISOString().slice(0,10);if(out.length!==10)fail('Schedule exceeds the supported date range.');return out;}
export const working=(d,off=[])=>!off.includes(new Date(d+'T12:00:00Z').getUTCDay());
export function business(d,off=[],strict=false){if(strict)d=plus(d);while(!working(d,off))d=plus(d);return d;}
export function duration(start,due,off=[]){let n=0;for(let d=start;d<=due;d=plus(d))if(working(d,off))n++;return Math.max(1,n);}
export function finish(start,n,off=[]){let d=business(start,off);while(--n>0)d=business(d,off,true);return d;}
export function normalizeTask(t,p){const off=calendar(p.offDays);if(t.due<t.start)fail('Due date must follow the start date.');t.start=business(t.start,off);t.due=business(t.due,off);}
// Recompute affected finish-to-start chains, including summary-task successors.
export function reschedule(s,before,roots,user,{early=false,completionDay=null,calendarProject=null}={}){
 const old=new Map(before.tasks.map(t=>[t.id,t])),map=new Map(s.tasks.map(t=>[t.id,t])),projects=new Map(s.projects.map(p=>[p.id,p]));
 const children=id=>s.tasks.filter(t=>t.parentId===id),deps=t=>[...t.predecessors,...children(t.id).map(c=>c.id)];
 const order=[],seen=new Set(),visiting=new Set();function visit(t){if(visiting.has(t.id))fail('These relationships would create a cycle.');if(seen.has(t.id))return;visiting.add(t.id);for(const id of deps(t)){if(!map.has(id))fail('Missing dependency.');visit(map.get(id));}visiting.delete(t.id);seen.add(t.id);order.push(t);}s.tasks.forEach(visit);
 const affected=new Set(roots),changed=[];const pct=t=>children(t.id).length?Math.max(...children(t.id).map(pct)):t.progress;
 const allowed=t=>user.role==='admin'||user.role==='head'&&user.department===projects.get(t.projectId).department||early&&user.role==='delegate'&&roots.some(id=>map.get(id).projectId===t.projectId);
 const end=t=>{const cs=children(t.id);if(early&&roots.includes(t.id)&&completionDay)return completionDay;if(cs.length&&cs.every(c=>complete(c)))return cs.map(end).sort().at(-1);return effectiveFinish(s,t);};const complete=t=>children(t.id).length?children(t.id).every(complete):t.progress===100;
 for(const t of order){const p=projects.get(t.projectId),off=calendar(p.offDays),prior=old.get(t.id)||t,cs=children(t.id);let start=t.start,due=t.due;
  if(cs.length){if(cs.some(c=>affected.has(c.id))){start=cs.reduce((d,c)=>c.start<d?c.start:d,start);due=cs.reduce((d,c)=>c.due>d?c.due:d,due);affected.add(t.id);}}
  else if(!roots.includes(t.id)&&(t.predecessors.some(id=>affected.has(id))||calendarProject===t.projectId)){
   if(pct(t)>0){const conflict=t.predecessors.some(id=>end(map.get(id))>=t.start);if(conflict)fail('A successor has already started. Resolve its dates before changing this plan.');continue;}
   const n=duration(prior.start,prior.due,(before.projects.find(x=>x.id===p.id)||p).offDays||[]);
   const predEnd=t.predecessors.map(id=>end(map.get(id))).sort().at(-1);
   start=predEnd?business(predEnd,off,true):business(t.start,off);start=start<p.start?business(p.start,off):start;
   if(early&&start>=t.start)continue;
   due=finish(start,n,off);affected.add(t.id);
  }
  if(start!==t.start||due!==t.due){if(!allowed(t))fail('This change affects another department. Ask an administrator to reschedule the full chain.');changed.push({taskId:t.id,fromStart:t.start,fromDue:t.due,start,due});t.start=start;t.due=due;}
 }
 for(const p of s.projects){const ts=s.tasks.filter(t=>t.projectId===p.id);if(ts.length){p.start=ts.reduce((d,t)=>t.start<d?t.start:d,p.start);p.due=ts.reduce((d,t)=>t.due>d?t.due:d,p.due);}}
 // Reject any newly introduced conflict, including dependencies on summary tasks.
 for(const t of s.tasks)if(affected.has(t.id))for(const id of t.predecessors)if(end(map.get(id))>=t.start)fail('The schedule conflicts with a predecessor.');
 return changed;
}
export const scheduleAudit=changes=>changes.length?` · Auto-rescheduled ${changes.length} tasks`:'';
export function effectiveFinish(s,t){const cs=s.tasks.filter(c=>c.parentId===t.id);const complete=t=>{const cs=s.tasks.filter(c=>c.parentId===t.id);return cs.length?cs.every(complete):t.progress===100;};if(cs.length&&cs.every(complete))return cs.map(c=>effectiveFinish(s,c)).sort().at(-1);const u=t.progress===100?s.updates.find(u=>u.taskId===t.id&&u.progress===100):null;return u?new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Amman',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(u.createdAt)):t.due;}

export function hasSuccessors(s,id){const ids=new Set([id]);let t=s.tasks.find(t=>t.id===id);while(t?.parentId&&!ids.has(t.parentId)){ids.add(t.parentId);t=s.tasks.find(x=>x.id===t.parentId);}return s.tasks.some(t=>t.predecessors.some(p=>ids.has(p)));}
