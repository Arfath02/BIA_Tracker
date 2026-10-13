"""Generate install SQL, data dictionary, and Graphviz/Mermaid ERD from the model.
Run from repository root: python -m scripts.export_database
No database connection is made.
"""
from pathlib import Path
from datetime import datetime,timezone
from sqlalchemy import insert
from sqlalchemy.schema import CreateTable,CreateIndex
from sqlalchemy.dialects import mssql
from production import database as d
from production.migrations import empty_state
out=Path('docs/database');out.mkdir(parents=True,exist_ok=True)
dialect=mssql.dialect()
def sql(statement): return '\n'.join(line.rstrip() for line in str(statement.compile(dialect=dialect,compile_kwargs={'literal_binds':True})).strip().splitlines())+';'
header='''-- BIA normalized schema v9. Generated from production/database.py.
-- NEW dedicated SQL Server database only. Select your database in SSMS first.
-- Existing v1-v8 installations: use python3 deploy/migrate.py instead.
-- Requires a migration/DBA identity. Does not create logins or contain secrets.
-- This entire installation is transactional and fails if bia tables exist.
SET XACT_ABORT ON;
BEGIN TRY
BEGIN TRANSACTION;
IF EXISTS (SELECT 1 FROM sys.tables WHERE schema_id=SCHEMA_ID(N'bia'))
    THROW 51000, 'bia tables already exist. Use the versioned migration, not this fresh-install script.', 1;
IF EXISTS (SELECT 1 FROM sys.tables WHERE schema_id=SCHEMA_ID(N'dbo') AND name IN (N'workspace',N'projects',N'users'))
    THROW 51001, 'Possible existing application found. Use the preserving migration.', 1;
IF SCHEMA_ID(N'bia') IS NULL EXEC(N'CREATE SCHEMA bia AUTHORIZATION dbo');
'''
statements=[header]
for table in d.metadata.sorted_tables:
    statements.append(sql(CreateTable(table)))
    for index in sorted(table.indexes,key=lambda i:i.name): statements.append(sql(CreateIndex(index)))
for row in d.ROLE_ROWS: statements.append(sql(insert(d.roles).values(**row)))
state=empty_state()
for row in state['catalogs']:
    statements.append(sql(insert(d.LOOKUPS[row['kind']]).values(**{k:row[k] for k in ('id','name','active')})))
m=state['masterProjects'][0];department=next(c['id'] for c in state['catalogs'] if c['name']==m['primaryDepartment'])
statements.append(sql(insert(d.masters).values(id=m['id'],title=m['title'],primaryDepartmentId=department,owner=m['owner'],description=m['description'])))
statements.append(sql(insert(d.workspace).values(id=1,version=1)))
statements.append('INSERT INTO bia.schema_migrations (version, appliedAt) VALUES (8, SYSUTCDATETIME());')
statements.append('''COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT>0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
-- Next: 02_runtime_permissions.sql, then create-admin through the Python CLI.
''')
Path('deploy/sql/01_schema.sql').write_text('\n\n'.join(statements))
md=['# SQL Server data dictionary — schema v9','',f'{len(d.metadata.tables)} normalized tables in schema `bia`. Generated from the application model. All money is USD and `DECIMAL(18,2)`. No JSON business-data columns.','', 'SQL identifiers are fixed by this model. Every table has a primary key; relationships use foreign keys. Dates are SQL DATE; UTC events are DATETIME2(6). VARCHAR(36) keys preserve existing IDs and accept new UUID strings. Keys never encode permissions.','']
for table in d.metadata.sorted_tables:
    md.extend([f'## bia.{table.name}','','| Column | SQL type | Null? | Key / relationship |','|---|---|---|---|'])
    for c in table.columns:
        flags=(['PK'] if c.primary_key else [])+[f'FK → `{f.target_fullname}`' for f in c.foreign_keys]+(['unique'] if c.unique else [])
        md.append(f'| `{c.name}` | `{c.type.compile(dialect=dialect)}` | {"Yes" if c.nullable else "No"} | {"; ".join(flags) or "—"} |')
    md.extend(['','Constraints: '+('; '.join(f'`{c.name}`: `{str(c.sqltext)}`' for c in table.constraints if hasattr(c,'sqltext')) or 'Primary / foreign / unique keys above.')])
    for c in table.constraints:
        if c.__class__.__name__=='UniqueConstraint': md.append('Unique tuple: '+', '.join('`'+x.name+'`' for x in c.columns)+'.')
    md.append('Indexes: '+(', '.join('`'+i.name+'` ('+', '.join(c.name for c in i.columns)+')' for i in sorted(table.indexes,key=lambda i:i.name)) or 'Primary/unique key indexes only.')+'\n')
md.extend(['## Intentional exceptions and derived fields','','- `master_projects.primaryDepartmentId` may be null only for migrated, previously unassigned masters. New/edit API commands require an active primary department. A DBA can make it NOT NULL after resolving all legacy rows.','- Legacy creator, author and audit identity links remain nullable when the original ID was not recorded. Never infer identity from a display name. New authenticated writes record these IDs.','- `owner` is an accountable lead/role display field, not a login or permission grant. Task ownership uses `assigneeId` → users.','- Audit `actor`/`role` and progress `author` deliberately preserve historical display snapshots even after an account rename.','- Task department is derived from its project. Invoice Paid/Unpaid status is derived from the existence of its settlement record. Summary progress, budget usage and management status are calculated, not duplicated as editable totals.','- A department is its own built-in access group: users.departmentId is membership; project_department_access is the many-to-many project grant. Management membership is users.role = management. No duplicate group membership table can drift out of sync.','- Full settlement only: invoice_payments has one row per invoice (invoiceId is PK and FK). No partial payments, multi-currency conversion or purchase-order line items are implied.','- Tables use no cascading deletes. The application deactivates accounts and lookups; it has no hard-delete business workflow.',''])
(out/'DATA_DICTIONARY.md').write_text('\n'.join(md))
# Complete editable ERD, with physical names and PK/FK tags.
erd=['erDiagram','    direction TB']
for t in d.metadata.sorted_tables:
    erd.append(f'    {t.name} {{')
    for c in t.columns:
        kind='date' if isinstance(c.type,d.ISODate) else 'datetime' if isinstance(c.type,d.UTCDateTime) else 'decimal' if isinstance(c.type,d.N) else 'int' if isinstance(c.type,d.I) else 'bool' if isinstance(c.type,d.B) else 'string'
        keys=[]
        if c.primary_key: keys.append('PK')
        if c.foreign_keys: keys.append('FK')
        erd.append(f'        {kind} {c.name}'+(' '+','.join(keys) if keys else ''))
    erd.append('    }')
for t in d.metadata.sorted_tables:
    for fk in sorted(t.foreign_key_constraints,key=lambda f:f.name):
        parent=next(iter(fk.elements)).column.table.name
        unique=all(c.primary_key for c in fk.columns) and len(t.primary_key.columns)==len(fk.columns)
        erd.append(f'    {parent} '+('o|' if any(c.nullable for c in fk.columns) else '||')+('--o|' if unique else '--o{')+f' {t.name} : "'+','.join(c.name for c in fk.columns)+'"')
(out/'BIA_ERD.mmd').write_text('\n'.join(erd)+'\n')
(out/'ERD.md').write_text('# BIA entity relationship diagram\n\nSource of truth: production/database.py. For an offline graphical view open BIA_ERD.html.\n\n```mermaid\n'+'\n'.join(erd)+'\n```\n')
# Graphviz views keep separate relationships readable. External endpoints repeated
# in a view are the SAME table, not additional copies in the database.
groups={
 '01_planning':('Project planning and progress',['departments','master_projects','projects','tasks','resources','task_predecessors','progress_updates','users']),
 '02_access':('Identity, department access and audit',['departments','roles','users','user_credentials','sessions','projects','project_department_access','audit_log']),
 '03_finance':('Purchasing and settlements',['projects','vendors','purchase_orders','invoices','invoice_payments','users']),
 '05_baselines':('Immutable baseline schedules',['projects','tasks','users','task_milestones','project_baselines','baseline_tasks','project_days_off']),
 '04_operations':('Operational metadata',['workspace','schema_migrations','login_attempts'])}
from html import escape
for slug,(title,names) in groups.items():
    dot=['digraph BIA {','graph [rankdir=TB, bgcolor="white", pad="0.3", nodesep="0.7", ranksep="0.9", splines=polyline];','node [shape=plain, fontname="Arial"];','edge [fontname="Arial", fontsize=11, color="#6c7a89", arrowsize=0.8];']
    for name in names:
        t=d.metadata.tables['bia.'+name];rows=[]
        for c in t.columns:
            if name=='users' and c.name not in ['id','departmentId','role','active']:continue
            if name=='projects' and slug!='01_planning' and c.name not in ['id','masterId','departmentId','createdById']:continue
            flags=('PK ' if c.primary_key else '')+('FK' if c.foreign_keys else '')
            rows.append(f'<TR><TD PORT="{c.name}" ALIGN="LEFT">{escape(c.name)}</TD><TD ALIGN="LEFT">{flags or " "}</TD></TR>')
        dot.append(f'{name} [label=<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="7"><TR><TD COLSPAN="2" BGCOLOR="#15354b"><FONT COLOR="white"><B>{name}</B></FONT></TD></TR>'+''.join(rows)+'</TABLE>>];')
    for name in names:
        t=d.metadata.tables['bia.'+name]
        for fk in sorted(t.foreign_key_constraints,key=lambda f:f.name):
            e=next(iter(fk.elements));parent=e.column.table.name
            if parent not in names:continue
            one=all(c.primary_key for c in fk.columns) and len(t.primary_key.columns)==len(fk.columns)
            optional=any(c.nullable for c in fk.columns)
            dot.append(f'{name} -> {parent} [label="{e.parent.name}\\n{("0..1" if one else "0..*")} to {("0..1" if optional else "1")}"];')
    dot.append('}')
    (out/(slug+'.dot')).write_text('\n'.join(dot))
print(f'Exported {len(d.metadata.tables)} tables, SQL install script, dictionary and ERD sources.')
