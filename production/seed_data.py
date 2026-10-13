"""Populate MS SQL database with the complete BIA Digital Transformation sample portfolio."""
from sqlalchemy import update
from . import database as d
from .masters import DEFAULT_MASTER_ID, default_master

SAMPLE_PROJECTS = [
    {
        'id': 'erp',
        'masterId': DEFAULT_MASTER_ID,
        'title': 'StellarKnit ERP',
        'department': 'Digital & IT',
        'owner': 'ERP workstream lead',
        'budget': 480000.0,
        'start': '2026-08-01',
        'due': '2026-10-30',
        'description': 'Unify planning, production, inventory and finance on a single operational backbone.',
        'color': '#b31c3f'
    },
    {
        'id': 'asrs',
        'masterId': DEFAULT_MASTER_ID,
        'title': 'ASRS & warehouse automation',
        'department': 'Warehouse',
        'owner': 'Warehouse vertical head',
        'budget': 1800000.0,
        'start': '2026-08-01',
        'due': '2026-12-18',
        'description': 'Connect warehouse storage, pallet movement and ERP stock visibility.',
        'color': '#386c77'
    },
    {
        'id': 'workforce',
        'masterId': DEFAULT_MASTER_ID,
        'title': 'Workforce visibility',
        'department': 'HR',
        'owner': 'HR vertical head',
        'budget': 35000.0,
        'start': '2026-09-01',
        'due': '2026-11-13',
        'description': 'Validate floor and zone visibility in a controlled workforce pilot.',
        'color': '#ac783d'
    },
    {
        'id': 'quality',
        'masterId': DEFAULT_MASTER_ID,
        'title': 'Connected quality',
        'department': 'Quality',
        'owner': 'Quality vertical head',
        'budget': 150000.0,
        'start': '2026-09-01',
        'due': '2026-11-27',
        'description': 'Link inspection, laboratory results and corrective actions to production.',
        'color': '#6665a8'
    },
    {
        'id': 'dyehouse',
        'masterId': DEFAULT_MASTER_ID,
        'title': 'Dyehouse trolley traceability',
        'department': 'Production',
        'owner': 'Production vertical head',
        'budget': 85000.0,
        'start': '2026-09-01',
        'due': '2026-11-20',
        'description': 'Track trolley handovers from batching through dyeing and inspection.',
        'color': '#537861'
    },
    {
        'id': 'infra',
        'masterId': DEFAULT_MASTER_ID,
        'title': 'Secure digital infrastructure',
        'department': 'Engineering',
        'owner': 'Infrastructure lead',
        'budget': 120000.0,
        'start': '2026-08-01',
        'due': '2026-10-30',
        'description': 'Build reliable identity, backups, network segmentation and application hosting.',
        'color': '#4e6f9d'
    }
]

SAMPLE_TASKS = [
    {'id': 'erp1', 'projectId': 'erp', 'parentId': None, 'title': 'Confirm master data & configurations', 'start': '2026-08-01', 'due': '2026-09-04', 'progress': 100, 'effort': 80, 'department': 'Digital & IT', 'resource': 'ERP workstream lead', 'predecessors': [], 'blocked': False},
    {'id': 'erp2', 'projectId': 'erp', 'parentId': None, 'title': 'Business acceptance testing', 'start': '2026-09-07', 'due': '2026-10-02', 'progress': 0, 'effort': 80, 'department': 'Digital & IT', 'resource': 'ERP workstream lead', 'predecessors': [], 'blocked': False},
    {'id': 'erp21', 'projectId': 'erp', 'parentId': 'erp2', 'title': 'Validate production & inventory flows', 'start': '2026-09-07', 'due': '2026-09-25', 'progress': 85, 'effort': 50, 'department': 'Digital & IT', 'resource': 'ERP workstream lead', 'predecessors': ['erp1'], 'blocked': True},
    {'id': 'erp22', 'projectId': 'erp', 'parentId': 'erp2', 'title': 'Validate finance reconciliation', 'start': '2026-09-07', 'due': '2026-10-02', 'progress': 70, 'effort': 30, 'department': 'Digital & IT', 'resource': 'ERP workstream lead', 'predecessors': ['erp1'], 'blocked': False},
    {'id': 'erp3', 'projectId': 'erp', 'parentId': None, 'title': 'Cutover rehearsal & sign-off', 'start': '2026-10-05', 'due': '2026-10-30', 'progress': 0, 'effort': 40, 'department': 'Digital & IT', 'resource': 'ERP workstream lead', 'predecessors': ['erp2'], 'blocked': False},
    {'id': 'asrs1', 'projectId': 'asrs', 'parentId': None, 'title': 'Layout and interface specification', 'start': '2026-08-01', 'due': '2026-09-18', 'progress': 100, 'effort': 60, 'department': 'Warehouse', 'resource': 'Warehouse vertical head', 'predecessors': [], 'blocked': False},
    {'id': 'asrs2', 'projectId': 'asrs', 'parentId': None, 'title': 'Vendor design approval', 'start': '2026-09-21', 'due': '2026-10-09', 'progress': 55, 'effort': 80, 'department': 'Warehouse', 'resource': 'Warehouse vertical head', 'predecessors': ['asrs1'], 'blocked': False},
    {'id': 'asrs3', 'projectId': 'asrs', 'parentId': None, 'title': 'WMS / WCS integration and FAT', 'start': '2026-10-12', 'due': '2026-12-18', 'progress': 0, 'effort': 100, 'department': 'Warehouse', 'resource': 'Warehouse vertical head', 'predecessors': ['asrs2'], 'blocked': False},
    {'id': 'wf1', 'projectId': 'workforce', 'parentId': None, 'title': 'Define zones and pilot measures', 'start': '2026-09-01', 'due': '2026-09-11', 'progress': 100, 'effort': 20, 'department': 'HR', 'resource': 'HR vertical head', 'predecessors': [], 'blocked': False},
    {'id': 'wf2', 'projectId': 'workforce', 'parentId': None, 'title': 'Install gateways and enroll pilot tags', 'start': '2026-09-14', 'due': '2026-10-09', 'progress': 65, 'effort': 35, 'department': 'HR', 'resource': 'HR vertical head', 'predecessors': ['wf1'], 'blocked': False},
    {'id': 'wf3', 'projectId': 'workforce', 'parentId': None, 'title': 'Evaluate pilot and scale decision', 'start': '2026-10-12', 'due': '2026-11-13', 'progress': 0, 'effort': 25, 'department': 'HR', 'resource': 'HR vertical head', 'predecessors': ['wf2'], 'blocked': False},
    {'id': 'qa1', 'projectId': 'quality', 'parentId': None, 'title': 'Approve quality data model', 'start': '2026-09-01', 'due': '2026-09-18', 'progress': 100, 'effort': 35, 'department': 'Quality', 'resource': 'Quality vertical head', 'predecessors': [], 'blocked': False},
    {'id': 'qa2', 'projectId': 'quality', 'parentId': None, 'title': 'Integrate inspection results', 'start': '2026-09-21', 'due': '2026-10-30', 'progress': 25, 'effort': 50, 'department': 'Quality', 'resource': 'Quality vertical head', 'predecessors': ['qa1'], 'blocked': False},
    {'id': 'qa3', 'projectId': 'quality', 'parentId': None, 'title': 'Run acceptance and traceability tests', 'start': '2026-11-02', 'due': '2026-11-27', 'progress': 0, 'effort': 25, 'department': 'Quality', 'resource': 'Quality vertical head', 'predecessors': ['qa2'], 'blocked': False},
    {'id': 'dy1', 'projectId': 'dyehouse', 'parentId': None, 'title': 'Map trolley handovers and scan points', 'start': '2026-09-01', 'due': '2026-09-18', 'progress': 100, 'effort': 30, 'department': 'Production', 'resource': 'Production vertical head', 'predecessors': [], 'blocked': False},
    {'id': 'dy2', 'projectId': 'dyehouse', 'parentId': None, 'title': 'Trial scan-to-move workflow', 'start': '2026-09-21', 'due': '2026-10-16', 'progress': 40, 'effort': 45, 'department': 'Production', 'resource': 'Production vertical head', 'predecessors': ['dy1'], 'blocked': False},
    {'id': 'dy3', 'projectId': 'dyehouse', 'parentId': None, 'title': 'Operational validation and rollout', 'start': '2026-10-19', 'due': '2026-11-20', 'progress': 0, 'effort': 25, 'department': 'Production', 'resource': 'Production vertical head', 'predecessors': ['dy2'], 'blocked': False},
    {'id': 'in1', 'projectId': 'infra', 'parentId': None, 'title': 'Network segmentation and identity', 'start': '2026-08-01', 'due': '2026-09-11', 'progress': 100, 'effort': 40, 'department': 'Engineering', 'resource': 'Infrastructure lead', 'predecessors': [], 'blocked': False},
    {'id': 'in2', 'projectId': 'infra', 'parentId': None, 'title': 'Backup and restore validation', 'start': '2026-09-14', 'due': '2026-09-25', 'progress': 70, 'effort': 35, 'department': 'Engineering', 'resource': 'Infrastructure lead', 'predecessors': ['in1'], 'blocked': True},
    {'id': 'in3', 'projectId': 'infra', 'parentId': None, 'title': 'Application hardening & handover', 'start': '2026-09-28', 'due': '2026-10-30', 'progress': 0, 'effort': 25, 'department': 'Engineering', 'resource': 'Infrastructure lead', 'predecessors': ['in2'], 'blocked': False}
]

SAMPLE_POS = [
    {'id': 'po1', 'projectId': 'erp', 'number': 'BIA-PO-001', 'vendor': 'ERP implementation partner', 'amount': 320000.0, 'date': '2026-08-03', 'description': 'Implementation and integration milestones'},
    {'id': 'po2', 'projectId': 'asrs', 'number': 'BIA-PO-002', 'vendor': 'Warehouse automation partner', 'amount': 980000.0, 'date': '2026-08-10', 'description': 'Design, equipment and controls'},
    {'id': 'po3', 'projectId': 'infra', 'number': 'BIA-PO-003', 'vendor': 'Infrastructure partner', 'amount': 78000.0, 'date': '2026-08-17', 'description': 'Compute, network and backup infrastructure'},
    {'id': 'po4', 'projectId': 'workforce', 'number': 'BIA-PO-004', 'vendor': 'Pilot device partner', 'amount': 18000.0, 'date': '2026-09-03', 'description': 'Gateway and tag pilot kit'}
]

SAMPLE_INVOICES = [
    {'id': 'inv1', 'poId': 'po1', 'number': 'BIA-INV-001', 'amount': 160000.0, 'date': '2026-08-17', 'due': '2026-09-16', 'status': 'Paid', 'reference': 'BIA-PAY-001', 'paidDate': '2026-09-15'},
    {'id': 'inv2', 'poId': 'po1', 'number': 'BIA-INV-002', 'amount': 80000.0, 'date': '2026-09-21', 'due': '2026-10-21', 'status': 'Unpaid', 'reference': None, 'paidDate': None},
    {'id': 'inv3', 'poId': 'po2', 'number': 'BIA-INV-003', 'amount': 294000.0, 'date': '2026-08-24', 'due': '2026-09-23', 'status': 'Unpaid', 'reference': None, 'paidDate': None},
    {'id': 'inv4', 'poId': 'po3', 'number': 'BIA-INV-004', 'amount': 39000.0, 'date': '2026-08-20', 'due': '2026-09-19', 'status': 'Paid', 'reference': 'BIA-PAY-002', 'paidDate': '2026-09-18'},
    {'id': 'inv5', 'poId': 'po4', 'number': 'BIA-INV-005', 'amount': 18000.0, 'date': '2026-09-10', 'due': '2026-10-10', 'status': 'Unpaid', 'reference': None, 'paidDate': None}
]

SAMPLE_UPDATES = [
    {'id': 'u1', 'taskId': 'erp21', 'progress': 85, 'note': 'Inventory reconciliation needs joint sign-off before the cutover rehearsal.', 'author': 'ERP workstream lead', 'createdAt': '2026-09-28T12:30:00Z'},
    {'id': 'u2', 'taskId': 'in2', 'progress': 70, 'note': 'Restore test evidence is pending for the secondary backup copy.', 'author': 'Infrastructure lead', 'createdAt': '2026-09-28T09:15:00Z'},
    {'id': 'u3', 'taskId': 'asrs2', 'progress': 55, 'note': 'Interface drawings are under review with the warehouse team.', 'author': 'Warehouse vertical head', 'createdAt': '2026-09-27T13:00:00Z'}
]

def seed_sample_data(engine):
    with engine.begin() as db:
        d.lock_workspace(db)
        state = d.read_state(db)
        
        target = {
            **state,
            'projects': SAMPLE_PROJECTS,
            'tasks': [{**t, 'assigneeId': None} for t in SAMPLE_TASKS],
            'pos': SAMPLE_POS,
            'invoices': SAMPLE_INVOICES,
            'updates': SAMPLE_UPDATES
        }
        
        d.persist_changes(db, state, target)
        db.execute(update(d.workspace).where(d.workspace.c.id == 1).values(version=d.workspace.c.version + 1))
        print("✅ Sample portfolio data successfully loaded into MS SQL database:")
        print(f"   • {len(SAMPLE_PROJECTS)} Subprojects")
        print(f"   • {len(SAMPLE_TASKS)} Tasks and Deliverables")
        print(f"   • {len(SAMPLE_POS)} Purchase Orders")
        print(f"   • {len(SAMPLE_INVOICES)} Invoices")
        print(f"   • {len(SAMPLE_UPDATES)} Progress Updates")
