import currencies from '../shared/currencies.json' with {type:'json'};
export {currencies};
export const currencyInfo=code=>currencies.find(c=>c.code===code);
export const currencyOf=p=>p?.currency||'USD';
export const usd=(amount,p)=>Number(amount||0)*Number(p?.usdRate||1);
export const currencyMoney=(amount,code='USD')=>new Intl.NumberFormat('en-US',{style:'currency',currency:code,currencyDisplay:'code',minimumFractionDigits:currencyInfo(code)?.digits??2,maximumFractionDigits:currencyInfo(code)?.digits??2}).format(amount||0);
export const usdMillions=n=>'USD '+new Intl.NumberFormat('en-US',{minimumFractionDigits:3,maximumFractionDigits:3}).format((n||0)/1e6)+' M';
export function withFinance(s){return {...s,projects:s.projects.map(p=>({...p,currency:p.currency||'USD',usdRate:p.usdRate||1,rateDate:p.rateDate||null,vendorId:p.vendorId||null})),paymentTerms:s.paymentTerms||[],consultants:s.consultants||[],trips:s.trips||[],expenses:s.expenses||[],changeRequests:s.changeRequests||[]};}
export function financeScope(s,projects){const ids=new Set(projects.map(p=>p.id)),vendors=new Set(projects.map(p=>p.vendorId));return {changeRequests:(s.changeRequests||[]).filter(t=>ids.has(t.projectId)),expenses:(s.expenses||[]).filter(t=>ids.has(t.projectId)),paymentTerms:(s.paymentTerms||[]).filter(t=>ids.has(t.projectId)),trips:(s.trips||[]).filter(t=>ids.has(t.projectId)),consultants:(s.consultants||[]).filter(c=>c.ownerProjectId?ids.has(c.ownerProjectId):vendors.has(c.vendorId)||(s.trips||[]).some(t=>ids.has(t.projectId)&&t.consultantId===c.id))};}
export function milestoneComplete(s,id){const t=s.tasks.find(t=>t.id===id);if(!t)return false;const children=s.tasks.filter(x=>x.parentId===id);return children.length?children.every(c=>milestoneComplete(s,c.id)):t.progress===100;}
export function termStatus(s,t,day){const invoice=s.invoices.find(i=>i.termId===t.id);if(invoice?.status==='Paid')return 'Paid';if(t.cancelled)return 'Cancelled';if(t.trigger==='milestone')return milestoneComplete(s,t.milestoneId)?'Due · milestone complete':'Waiting for milestone';return t.dueDate<=day?(t.dueDate<day?'Overdue':'Due today'):'Scheduled';}
export function paymentAlerts(s,day){const terms=(s.paymentTerms||[]).filter(t=>!t.cancelled&&/^(Due|Overdue)/.test(termStatus(s,t,day))).map(t=>({id:t.id,projectId:t.projectId,label:t.title,status:termStatus(s,t,day),amount:t.amount}));const invoices=s.invoices.filter(i=>i.status!=='Paid'&&i.due<=day&&!terms.some(t=>t.id===i.termId)).map(i=>({id:i.id,projectId:s.pos.find(p=>p.id===i.poId)?.projectId,label:i.number,status:i.due<day?'Invoice overdue':'Invoice due today',amount:i.amount}));return [...terms,...invoices].filter(x=>s.projects.some(p=>p.id===x.projectId));}

// Fixed reporting policy requested by BIA, not a live market quote.
export const jodUsd=n=>Math.round(Number(n||0)*14000)/10000;
export function tripExpenseUsd(t,p){return (t.flightBooked?(t.flightCostJod!=null?jodUsd(t.flightCostJod):usd(t.flightCost,p)):0)+jodUsd(t.hotelBookedBy==='bia'?t.hotelCostJod:0)+jodUsd(t.visaCostJod);}
export function otherExpenses(s,projectId){const ids=new Set(s.projects.filter(p=>!projectId||p.id===projectId).map(p=>p.id));return Math.round(((s.trips||[]).filter(t=>ids.has(t.projectId)).reduce((n,t)=>n+tripExpenseUsd(t,s.projects.find(p=>p.id===t.projectId)),0)+(s.expenses||[]).filter(e=>ids.has(e.projectId)).reduce((n,e)=>n+jodUsd(e.amountJod),0))*10000)/10000;}

export const changeInvoiced=(s,id)=>s.invoices.filter(i=>i.changeRequestId===id).reduce((n,i)=>n+i.amount,0);
export const approvedChanges=(s,id)=>(s.changeRequests||[]).filter(c=>c.projectId===id&&c.status==='Approved').reduce((n,c)=>n+c.amount,0);
