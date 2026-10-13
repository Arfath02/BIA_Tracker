export function seed(){
 const projects=[
  {id:'erp',title:'StellarKnit ERP',department:'Digital & IT',owner:'ERP workstream lead',budget:480000,start:'2026-08-01',due:'2026-10-30',description:'Unify planning, production, inventory and finance on a single operational backbone.',color:'#b31c3f'},
  {id:'asrs',title:'ASRS & warehouse automation',department:'Warehouse',owner:'Warehouse vertical head',budget:1800000,start:'2026-08-01',due:'2026-12-18',description:'Connect warehouse storage, pallet movement and ERP stock visibility.',color:'#386c77'},
  {id:'workforce',title:'Workforce visibility',department:'HR',owner:'HR vertical head',budget:35000,start:'2026-09-01',due:'2026-11-13',description:'Validate floor and zone visibility in a controlled workforce pilot.',color:'#ac783d'},
  {id:'quality',title:'Connected quality',department:'Quality',owner:'Quality vertical head',budget:150000,start:'2026-09-01',due:'2026-11-27',description:'Link inspection, laboratory results and corrective actions to production.',color:'#6665a8'},
  {id:'dyehouse',title:'Dyehouse trolley traceability',department:'Production',owner:'Production vertical head',budget:85000,start:'2026-09-01',due:'2026-11-20',description:'Track trolley handovers from batching through dyeing and inspection.',color:'#537861'},
  {id:'infra',title:'Secure digital infrastructure',department:'Engineering',owner:'Infrastructure lead',budget:120000,start:'2026-08-01',due:'2026-10-30',description:'Build reliable identity, backups, network segmentation and application hosting.',color:'#4e6f9d'}
 ];
 const tasks=[];function add(id,projectId,title,start,due,p,effort,pred=[],blocked=false,parentId=null){tasks.push({id,projectId,title,start,due,progress:p,effort,predecessors:pred,blocked,parentId,department:projects.find(x=>x.id===projectId).department,resource:projects.find(x=>x.id===projectId).owner,assigneeId:null})}
 add('erp1','erp','Confirm master data & configurations','2026-08-01','2026-09-04',100,80);
 add('erp2','erp','Business acceptance testing','2026-09-07','2026-10-02',0,80,['erp1']);
 // Summary dependencies are represented at leaf level, so summaries stay editable by roll-up only.
 tasks.find(t=>t.id==='erp2').predecessors=[];
 add('erp21','erp','Validate production & inventory flows','2026-09-07','2026-09-25',85,50,['erp1'],true,'erp2');
 add('erp22','erp','Validate finance reconciliation','2026-09-07','2026-10-02',70,30,['erp1'],false,'erp2');
 add('erp3','erp','Cutover rehearsal & sign-off','2026-10-05','2026-10-30',0,40,['erp2']);
 add('asrs1','asrs','Layout and interface specification','2026-08-01','2026-09-18',100,60);
 add('asrs2','asrs','Vendor design approval','2026-09-21','2026-10-09',55,80,['asrs1']);
 add('asrs3','asrs','WMS / WCS integration and FAT','2026-10-12','2026-12-18',0,100,['asrs2']);
 add('wf1','workforce','Define zones and pilot measures','2026-09-01','2026-09-11',100,20);
 add('wf2','workforce','Install gateways and enroll pilot tags','2026-09-14','2026-10-09',65,35,['wf1']);
 add('wf3','workforce','Evaluate pilot and scale decision','2026-10-12','2026-11-13',0,25,['wf2']);
 add('qa1','quality','Approve quality data model','2026-09-01','2026-09-18',100,35);
 add('qa2','quality','Integrate inspection results','2026-09-21','2026-10-30',25,50,['qa1']);
 add('qa3','quality','Run acceptance and traceability tests','2026-11-02','2026-11-27',0,25,['qa2']);
 add('dy1','dyehouse','Map trolley handovers and scan points','2026-09-01','2026-09-18',100,30);
 add('dy2','dyehouse','Trial scan-to-move workflow','2026-09-21','2026-10-16',40,45,['dy1']);
 add('dy3','dyehouse','Operational validation and rollout','2026-10-19','2026-11-20',0,25,['dy2']);
 add('in1','infra','Network segmentation and identity','2026-08-01','2026-09-11',100,40);
 add('in2','infra','Backup and restore validation','2026-09-14','2026-09-25',70,35,['in1'],true);
 add('in3','infra','Application hardening & handover','2026-09-28','2026-10-30',0,25,['in2']);
 const pos=[{id:'po1',projectId:'erp',number:'DEMO-PO-001',vendor:'ERP implementation partner',amount:320000,date:'2026-08-03',description:'Implementation and integration milestones'},{id:'po2',projectId:'asrs',number:'DEMO-PO-002',vendor:'Warehouse automation partner',amount:980000,date:'2026-08-10',description:'Design, equipment and controls'},{id:'po3',projectId:'infra',number:'DEMO-PO-003',vendor:'Infrastructure partner',amount:78000,date:'2026-08-17',description:'Compute, network and backup infrastructure'},{id:'po4',projectId:'workforce',number:'DEMO-PO-004',vendor:'Pilot device partner',amount:18000,date:'2026-09-03',description:'Gateway and tag pilot kit'}];
 const invoices=[{id:'inv1',poId:'po1',number:'DEMO-INV-001',amount:160000,date:'2026-08-17',due:'2026-09-16',status:'Paid',reference:'DEMO-PAY-001',paidDate:'2026-09-15'},{id:'inv2',poId:'po1',number:'DEMO-INV-002',amount:80000,date:'2026-09-21',due:'2026-10-21',status:'Unpaid'},{id:'inv3',poId:'po2',number:'DEMO-INV-003',amount:294000,date:'2026-08-24',due:'2026-09-23',status:'Unpaid'},{id:'inv4',poId:'po3',number:'DEMO-INV-004',amount:39000,date:'2026-08-20',due:'2026-09-19',status:'Paid',reference:'DEMO-PAY-002',paidDate:'2026-09-18'},{id:'inv5',poId:'po4',number:'DEMO-INV-005',amount:18000,date:'2026-09-10',due:'2026-10-10',status:'Unpaid'}];
 return {projects,tasks,pos,invoices,users:[],version:1,updates:[{id:'u1',taskId:'erp21',progress:85,note:'Sample: inventory reconciliation needs joint sign-off before the cutover rehearsal.',author:'ERP workstream lead',createdAt:'2026-09-28T12:30:00Z'},{id:'u2',taskId:'in2',progress:70,note:'Sample: restore test evidence is pending for the secondary backup copy.',author:'Infrastructure lead',createdAt:'2026-09-28T09:15:00Z'},{id:'u3',taskId:'asrs2',progress:55,note:'Sample: interface drawings are under review with the warehouse team.',author:'Warehouse vertical head',createdAt:'2026-09-27T13:00:00Z'}],audit:[{id:'a1',actor:'BIA review workspace',role:'system',action:'Illustrative portfolio created for review',at:'2026-09-29T07:00:00Z'}]};
}
