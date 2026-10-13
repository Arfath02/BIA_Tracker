-- Run using the actual RUNTIME login in the BIA database, not the DBA login.
-- Read-only checks. Every line should show passed=1.
SELECT N'Not sysadmin' AS control, IIF(IS_SRVROLEMEMBER('sysadmin')=0,1,0) AS passed
UNION ALL SELECT N'Not db_owner', IIF(IS_ROLEMEMBER('db_owner')=0,1,0)
UNION ALL SELECT N'Cannot create tables', IIF(HAS_PERMS_BY_NAME(DB_NAME(),'DATABASE','CREATE TABLE')=0,1,0)
UNION ALL SELECT N'Cannot alter app schema', IIF(HAS_PERMS_BY_NAME('bia','SCHEMA','ALTER')=0,1,0)
UNION ALL SELECT N'Can read projects', IIF(HAS_PERMS_BY_NAME('bia.projects','OBJECT','SELECT')=1,1,0)
UNION ALL SELECT N'Can insert tasks', IIF(HAS_PERMS_BY_NAME('bia.tasks','OBJECT','INSERT')=1,1,0)
UNION ALL SELECT N'Cannot delete projects', IIF(HAS_PERMS_BY_NAME('bia.projects','OBJECT','DELETE')=0,1,0)
UNION ALL SELECT N'Cannot edit audit', IIF(HAS_PERMS_BY_NAME('bia.audit_log','OBJECT','UPDATE')=0,1,0)
UNION ALL SELECT N'Cannot delete audit', IIF(HAS_PERMS_BY_NAME('bia.audit_log','OBJECT','DELETE')=0,1,0)
UNION ALL SELECT N'Cannot edit progress history', IIF(HAS_PERMS_BY_NAME('bia.progress_updates','OBJECT','UPDATE')=0,1,0)
UNION ALL SELECT N'Cannot edit payments', IIF(HAS_PERMS_BY_NAME('bia.invoice_payments','OBJECT','UPDATE')=0,1,0)
UNION ALL SELECT N'Cannot modify role definitions', IIF(HAS_PERMS_BY_NAME('bia.roles','OBJECT','UPDATE')=0,1,0)
UNION ALL SELECT N'Schema version is 8', IIF(EXISTS(SELECT 1 FROM bia.schema_migrations WHERE version=9),1,0);
-- On upgrades, this result must be empty.
SELECT N'UNEXPECTED legacy read permission' AS finding, t.name
FROM sys.tables t WHERE t.schema_id=SCHEMA_ID('dbo') AND t.name IN
('workspace','users','master_projects','projects','tasks','task_predecessors',
 'purchase_orders','invoices','progress_updates','audit_log','sessions',
 'login_attempts','catalogs','project_department_access')
AND HAS_PERMS_BY_NAME('dbo.'+QUOTENAME(t.name),'OBJECT','SELECT')=1;
-- Every FK and CHECK should be enabled and trusted; this result must be empty.
SELECT name, N'FK' AS kind FROM sys.foreign_keys
WHERE schema_id=SCHEMA_ID('bia') AND (is_disabled=1 OR is_not_trusted=1)
UNION ALL
SELECT name, N'CHECK' FROM sys.check_constraints
WHERE schema_id=SCHEMA_ID('bia') AND (is_disabled=1 OR is_not_trusted=1);

IF HAS_PERMS_BY_NAME(N'bia.project_baselines',N'OBJECT',N'UPDATE')=1 OR HAS_PERMS_BY_NAME(N'bia.baseline_tasks',N'OBJECT',N'DELETE')=1
    THROW 51012, 'Runtime identity can change immutable baselines. Review grants.', 1;
