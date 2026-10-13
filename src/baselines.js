// Immutable schedule snapshots. Comparison defaults to the first approved baseline.
const day=d=>Date.parse(d+'T00:00:00Z')/86400000;
export const daysBetween=(a,b)=>Math.round(day(b)-day(a));
export const ammanToday=()=>new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Amman',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
export function baselineFor(s,projectId){const versions=(s.baselines||[]).filter(b=>b.projectId===projectId).sort((a,b)=>a.version-b.version);return versions.find(b=>b.id===s.baselineChoices?.[projectId])||versions[0]||null}
function complete(s,t){const children=s.tasks.filter(c=>c.parentId===t.id);return children.length?children.every(c=>complete(s,c)):t.progress===100}
function finished(s,t){const children=s.tasks.filter(c=>c.parentId===t.id);if(children.length){const dates=children.map(c=>finished(s,c));return dates.every(Boolean)?dates.sort().at(-1):null;}const u=s.updates.filter(u=>u.taskId===t.id&&u.progress===100).sort((a,b)=>b.createdAt.localeCompare(a.createdAt))[0];return u?new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Amman',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(u.createdAt)):null}
export function taskVariance(s,t,asOf=ammanToday()){
 const baseline=baselineFor(s,t.projectId),original=baseline?.tasks.find(x=>x.taskId===t.id);
 if(!original)return {baseline,original:null,delayDays:0,delayed:false,label:baseline?'Added after baseline':'No baseline'};
 const finishShift=daysBetween(original.due,t.due),startShift=daysBetween(original.start,t.start),done=complete(s,t),actualFinish=done?finished(s,t):null;
 const overdueDays=!done?Math.max(0,daysBetween(original.due,asOf)):0;
 const actualDelay=actualFinish?Math.max(0,daysBetween(original.due,actualFinish)):0;
 const delayDays=done&&actualFinish?actualDelay:Math.max(0,finishShift,overdueDays,actualDelay);
 return {baseline,original,startShift,finishShift,overdueDays,actualFinish,delayDays,delayed:delayDays>0,label:delayDays?(done?(actualFinish?`Completed late ${delayDays}d`:`Finish shifted ${delayDays}d`):`Delayed ${delayDays}d`):finishShift<0?`${-finishShift}d earlier`:'On baseline'};
}
export function projectCompletion(s,p){
 const tasks=s.tasks.filter(t=>t.projectId===p.id&&!s.tasks.some(c=>c.parentId===t.id));
 if(!tasks.length||!tasks.every(t=>t.progress===100))return {completed:false,early:false,earlyDays:0};
 const dates=tasks.map(t=>finished(s,t));const actualFinish=dates.every(Boolean)?dates.sort().at(-1):null;
 const original=(s.baselines||[]).filter(b=>b.projectId===p.id).sort((a,b)=>a.version-b.version)[0];
 const plannedFinish=original?.due||p.due,earlyDays=actualFinish?Math.max(0,daysBetween(actualFinish,plannedFinish)):0;
 return {completed:true,actualFinish,plannedFinish,basis:original?'original baseline':'current plan (no baseline)',early:earlyDays>0,earlyDays,label:earlyDays?`Completed ${earlyDays} days early`:actualFinish===plannedFinish?'Completed on time':actualFinish?'Completed late':'Complete — completion date unavailable'};
}
export function projectVariance(s,p,asOf=ammanToday()){
 const baseline=baselineFor(s,p.id);if(!baseline)return {baseline:null,delayed:false,delayDays:0,delayedTasks:0,delayedMilestones:0};
 const tasks=s.tasks.filter(t=>t.projectId===p.id),rows=tasks.map(t=>({...taskVariance(s,t,asOf),milestone:!!t.isMilestone}));
 const allDone=tasks.length>0&&tasks.every(t=>complete(s,t));const finishShift=daysBetween(baseline.due,p.due),overdueDays=allDone?0:Math.max(0,daysBetween(baseline.due,asOf));
 const actualFinish=allDone?projectCompletion(s,p).actualFinish:null;
 const delayDays=actualFinish?Math.max(0,daysBetween(baseline.due,actualFinish)):Math.max(0,finishShift,overdueDays,...rows.map(r=>r.delayDays));
 return {baseline,finishShift,overdueDays,delayDays,delayed:delayDays>0,delayedTasks:rows.filter(r=>r.delayed).length,delayedMilestones:rows.filter(r=>r.delayed&&r.milestone).length};
}
export function baselineProgress(s,p,asOf=ammanToday()){
 const baseline=baselineFor(s,p.id);if(!baseline)return null;
 const leaves=baseline.tasks.filter(t=>!baseline.tasks.some(c=>c.parentId===t.taskId));const weight=leaves.reduce((n,t)=>n+t.effort,0);
 const fraction=t=>asOf<t.start?0:asOf>=t.due?1:t.isMilestone?0:(daysBetween(t.start,asOf)+1)/(daysBetween(t.start,t.due)+1);
 const descendants=t=>{const children=s.tasks.filter(c=>c.parentId===t.id);return children.length?children.flatMap(descendants):[t]};const currentProgress=t=>{const leaves=descendants(t),w=leaves.reduce((n,c)=>n+c.effort,0);return w?leaves.reduce((n,c)=>n+c.progress*c.effort,0)/w:0};
 const planned=weight?Math.round(leaves.reduce((n,t)=>n+fraction(t)*100*t.effort,0)/weight):0;
 const actual=weight?Math.round(leaves.reduce((n,t)=>n+(s.tasks.find(c=>c.id===t.taskId)?currentProgress(s.tasks.find(c=>c.id===t.taskId)):0)*t.effort,0)/weight):0;
 return {planned,actual,gap:Math.max(0,planned-actual)};
}
