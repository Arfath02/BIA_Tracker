import React from 'react';
import {canPlan} from './domain';
import {projectCompletion} from './baselines';
export function PortfolioNotices({state:s,onCapture}){
 const missing=s.projects.filter(p=>!(s.baselines||[]).some(b=>b.projectId===p.id));
 const early=s.projects.map(p=>({p,result:projectCompletion(s,p)})).filter(x=>x.result.early);
 return <div className="portfolio-notices">{missing.length>0&&<details className="baseline-reminder"><summary>{missing.length} project{missing.length===1?'':'s'} not baselined — please save an approved baseline</summary><p>Baseline each approved task plan before revising dates. Read-only users should ask the project owner.</p><ul>{missing.map(p=><li key={p.id}><span>{p.title}</span>{canPlan(s.user,p.department)?<button className="text-link" disabled={!s.tasks.some(t=>t.projectId===p.id)} onClick={()=>onCapture(p)}>Save baseline<span className="sr-only"> for {p.title}</span></button>:<small>Owner: {p.owner}</small>}{!s.tasks.some(t=>t.projectId===p.id)&&<small>Add a task plan first</small>}</li>)}</ul></details>}{early.length>0&&<details className="completion-notice" open><summary>{early.length} project{early.length===1?'':'s'} completed ahead of plan</summary><ul>{early.map(({p,result:r})=><li key={p.id}><strong>{p.title}</strong><span>{r.label} · {r.actualFinish} · vs {r.basis}</span></li>)}</ul></details>}</div>;
}
