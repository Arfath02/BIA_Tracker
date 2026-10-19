-- DBA: run in the dedicated BIA database AFTER the v12 install/migration.
-- Map the existing runtime login to a database USER named bia_runtime first,
-- or replace [bia_runtime] below with the approved database user name.
-- Never use sa, db_owner, db_ddladmin, db_datareader or db_datawriter for the app.
-- This script creates no login and contains no password.
SET XACT_ABORT ON;
BEGIN TRANSACTION;
IF NOT EXISTS (SELECT 1 FROM bia.schema_migrations WHERE version=12)
    THROW 51000, 'Install schema v12 first.', 1;
IF DATABASE_PRINCIPAL_ID(N'bia_runtime') IS NULL
    THROW 51001, 'Map the approved runtime login to database user bia_runtime first (or edit its name in this script).', 1;
IF DATABASE_PRINCIPAL_ID(N'bia_app_runtime') IS NULL
    CREATE ROLE [bia_app_runtime];

GRANT SELECT ON OBJECT::bia.schema_migrations TO [bia_app_runtime];
GRANT SELECT, UPDATE ON OBJECT::bia.workspace TO [bia_app_runtime];
GRANT SELECT ON OBJECT::bia.roles TO [bia_app_runtime];
GRANT SELECT, INSERT, UPDATE ON OBJECT::bia.departments TO [bia_app_runtime];
GRANT SELECT, INSERT, UPDATE ON OBJECT::bia.vendors TO [bia_app_runtime];
GRANT SELECT, INSERT, UPDATE ON OBJECT::bia.resources TO [bia_app_runtime];
GRANT SELECT, INSERT, UPDATE ON OBJECT::bia.users TO [bia_app_runtime];
GRANT SELECT, INSERT, UPDATE ON OBJECT::bia.user_credentials TO [bia_app_runtime];
GRANT SELECT, INSERT, UPDATE ON OBJECT::bia.master_projects TO [bia_app_runtime];
GRANT SELECT, INSERT, UPDATE ON OBJECT::bia.projects TO [bia_app_runtime];
GRANT SELECT, INSERT, UPDATE ON OBJECT::bia.tasks TO [bia_app_runtime];
GRANT SELECT, INSERT, UPDATE ON OBJECT::bia.purchase_orders TO [bia_app_runtime];
GRANT SELECT, INSERT, UPDATE ON OBJECT::bia.invoices TO [bia_app_runtime];
GRANT SELECT, INSERT, DELETE ON OBJECT::bia.project_department_access TO [bia_app_runtime];
GRANT SELECT, INSERT, DELETE ON OBJECT::bia.task_predecessors TO [bia_app_runtime];
GRANT SELECT, INSERT, DELETE ON OBJECT::bia.sessions TO [bia_app_runtime];
GRANT SELECT, INSERT, UPDATE, DELETE ON OBJECT::bia.login_attempts TO [bia_app_runtime];
GRANT SELECT, INSERT ON OBJECT::bia.invoice_payments TO [bia_app_runtime];
GRANT SELECT, INSERT ON OBJECT::bia.progress_updates TO [bia_app_runtime];
GRANT SELECT, INSERT ON OBJECT::bia.audit_log TO [bia_app_runtime];
DENY UPDATE, DELETE ON OBJECT::bia.invoice_payments TO [bia_app_runtime];
DENY UPDATE, DELETE ON OBJECT::bia.progress_updates TO [bia_app_runtime];
DENY UPDATE, DELETE ON OBJECT::bia.audit_log TO [bia_app_runtime];
DENY INSERT, UPDATE, DELETE ON OBJECT::bia.roles TO [bia_app_runtime];
DENY INSERT, UPDATE, DELETE ON OBJECT::bia.schema_migrations TO [bia_app_runtime];
DENY ALTER ON SCHEMA::bia TO [bia_app_runtime];

-- A v1-v6 upgrade leaves old dbo tables for DBA reconciliation/recovery only.
-- Remove all app access to those retained tables. Dynamic SQL contains only
-- identifiers read from this fixed allowlist and escaped with QUOTENAME.
DECLARE @legacy sysname, @sql nvarchar(max);
DECLARE legacy_tables CURSOR LOCAL FAST_FORWARD FOR
SELECT name FROM sys.tables WHERE schema_id=SCHEMA_ID(N'dbo') AND name IN
(N'workspace',N'users',N'master_projects',N'projects',N'tasks',N'task_predecessors',
 N'purchase_orders',N'invoices',N'progress_updates',N'audit_log',N'sessions',
 N'login_attempts',N'catalogs',N'project_department_access');
OPEN legacy_tables;
FETCH NEXT FROM legacy_tables INTO @legacy;
WHILE @@FETCH_STATUS=0
BEGIN
    SET @sql=N'DENY SELECT, INSERT, UPDATE, DELETE ON OBJECT::dbo.'+QUOTENAME(@legacy)+N' TO [bia_app_runtime];';
    EXEC sys.sp_executesql @sql;
    FETCH NEXT FROM legacy_tables INTO @legacy;
END;
CLOSE legacy_tables;
DEALLOCATE legacy_tables;
IF NOT EXISTS (SELECT 1 FROM sys.database_role_members
    WHERE role_principal_id=DATABASE_PRINCIPAL_ID(N'bia_app_runtime')
      AND member_principal_id=DATABASE_PRINCIPAL_ID(N'bia_runtime'))
    ALTER ROLE [bia_app_runtime] ADD MEMBER [bia_runtime];
-- Baseline v12: immutable snapshots; milestone classification is editable.
GRANT SELECT, INSERT ON OBJECT::bia.project_baselines TO bia_app_runtime;
GRANT SELECT, INSERT ON OBJECT::bia.baseline_tasks TO bia_app_runtime;
DENY UPDATE, DELETE ON OBJECT::bia.project_baselines TO bia_app_runtime;
DENY UPDATE, DELETE ON OBJECT::bia.baseline_tasks TO bia_app_runtime;
GRANT SELECT, INSERT, DELETE ON OBJECT::bia.task_milestones TO bia_app_runtime;

GRANT SELECT, INSERT, DELETE ON OBJECT::bia.project_days_off TO bia_app_runtime;
GRANT SELECT ON OBJECT::bia.currency_codes TO bia_app_runtime;
DENY INSERT, UPDATE, DELETE ON OBJECT::bia.currency_codes TO bia_app_runtime;
GRANT SELECT, INSERT, UPDATE ON OBJECT::bia.project_finance TO bia_app_runtime;
GRANT SELECT, INSERT, UPDATE ON OBJECT::bia.payment_terms TO bia_app_runtime;
GRANT SELECT, INSERT, UPDATE ON OBJECT::bia.vendor_consultants TO bia_app_runtime;
GRANT SELECT, INSERT, UPDATE ON OBJECT::bia.consultant_trips TO bia_app_runtime;
GRANT SELECT, INSERT ON OBJECT::bia.invoice_terms TO bia_app_runtime;
DENY UPDATE, DELETE ON OBJECT::bia.invoice_terms TO bia_app_runtime;

GRANT SELECT, INSERT, UPDATE ON OBJECT::bia.consultant_details TO bia_app_runtime;
GRANT SELECT, INSERT, UPDATE ON OBJECT::bia.trip_costs TO bia_app_runtime;
GRANT SELECT, INSERT, UPDATE ON OBJECT::bia.project_expenses TO bia_app_runtime;
GRANT SELECT, INSERT, UPDATE ON OBJECT::bia.budget_change_requests TO bia_app_runtime;
GRANT SELECT, INSERT ON OBJECT::bia.invoice_budget_changes TO bia_app_runtime;
DENY UPDATE, DELETE ON OBJECT::bia.invoice_budget_changes TO bia_app_runtime;
COMMIT TRANSACTION;
