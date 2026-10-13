-- BIA normalized schema v9. Generated from production/database.py.
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


CREATE TABLE bia.departments (
	id VARCHAR(36) NOT NULL,
	name NVARCHAR(60) COLLATE Latin1_General_100_CI_AS_SC NOT NULL,
	active BIT NOT NULL,
	CONSTRAINT pk_departments PRIMARY KEY (id),
	CONSTRAINT ck_departments_name_required CHECK (LEN(name)>0),
	CONSTRAINT uq_departments_name UNIQUE (name)
);

CREATE TABLE bia.login_attempts (
	[key] VARCHAR(64) NOT NULL,
	count INTEGER NOT NULL,
	expires NUMERIC(18, 0) NOT NULL,
	CONSTRAINT pk_login_attempts PRIMARY KEY ([key]),
	CONSTRAINT ck_login_attempts_count_positive CHECK (count>=1)
);

CREATE INDEX ix_login_attempts_expires ON bia.login_attempts (expires);

CREATE TABLE bia.resources (
	id VARCHAR(36) NOT NULL,
	name NVARCHAR(80) COLLATE Latin1_General_100_CI_AS_SC NOT NULL,
	active BIT NOT NULL,
	CONSTRAINT pk_resources PRIMARY KEY (id),
	CONSTRAINT ck_resources_name_required CHECK (LEN(name)>0),
	CONSTRAINT uq_resources_name UNIQUE (name)
);

CREATE TABLE bia.roles (
	code VARCHAR(20) NOT NULL,
	name NVARCHAR(80) NOT NULL,
	CONSTRAINT pk_roles PRIMARY KEY (code),
	CONSTRAINT ck_roles_known_role CHECK (code IN ('admin','head','delegate','finance','executive','management'))
);

CREATE TABLE bia.schema_migrations (
	version INTEGER NOT NULL,
	[appliedAt] DATETIME2(6) NOT NULL,
	CONSTRAINT pk_schema_migrations PRIMARY KEY (version)
);

CREATE TABLE bia.vendors (
	id VARCHAR(36) NOT NULL,
	name NVARCHAR(100) COLLATE Latin1_General_100_CI_AS_SC NOT NULL,
	active BIT NOT NULL,
	CONSTRAINT pk_vendors PRIMARY KEY (id),
	CONSTRAINT ck_vendors_name_required CHECK (LEN(name)>0),
	CONSTRAINT uq_vendors_name UNIQUE (name)
);

CREATE TABLE bia.workspace (
	id INTEGER NOT NULL,
	version INTEGER NOT NULL,
	CONSTRAINT pk_workspace PRIMARY KEY (id),
	CONSTRAINT ck_workspace_singleton CHECK (id=1),
	CONSTRAINT ck_workspace_version_positive CHECK (version>=1)
);

CREATE TABLE bia.master_projects (
	id VARCHAR(36) NOT NULL,
	title NVARCHAR(100) COLLATE Latin1_General_100_CI_AS_SC NOT NULL,
	[primaryDepartmentId] VARCHAR(36) NULL,
	owner NVARCHAR(80) NOT NULL,
	description NVARCHAR(1000) NULL,
	CONSTRAINT pk_master_projects PRIMARY KEY (id),
	CONSTRAINT uq_master_projects_title UNIQUE (title),
	CONSTRAINT [fk_master_projects_primaryDepartmentId_departments] FOREIGN KEY([primaryDepartmentId]) REFERENCES bia.departments (id)
);

CREATE INDEX [ix_master_projects_primaryDepartmentId] ON bia.master_projects ([primaryDepartmentId]);

CREATE TABLE bia.users (
	id VARCHAR(36) NOT NULL,
	email NVARCHAR(254) COLLATE Latin1_General_100_CI_AS_SC NOT NULL,
	name NVARCHAR(80) NOT NULL,
	role VARCHAR(20) NOT NULL,
	[departmentId] VARCHAR(36) NOT NULL,
	active BIT NOT NULL,
	CONSTRAINT pk_users PRIMARY KEY (id),
	CONSTRAINT uq_users_email UNIQUE (email),
	CONSTRAINT fk_users_role_roles FOREIGN KEY(role) REFERENCES bia.roles (code),
	CONSTRAINT [fk_users_departmentId_departments] FOREIGN KEY([departmentId]) REFERENCES bia.departments (id)
);

CREATE INDEX [ix_users_departmentId] ON bia.users ([departmentId]);

CREATE TABLE bia.projects (
	id VARCHAR(36) NOT NULL,
	[masterId] VARCHAR(36) NOT NULL,
	[createdById] VARCHAR(36) NULL,
	title NVARCHAR(100) NOT NULL,
	[departmentId] VARCHAR(36) NOT NULL,
	owner NVARCHAR(80) NOT NULL,
	budget NUMERIC(18, 2) NOT NULL,
	start DATE NOT NULL,
	due DATE NOT NULL,
	description NVARCHAR(1000) NULL,
	color VARCHAR(10) NULL,
	CONSTRAINT pk_projects PRIMARY KEY (id),
	CONSTRAINT ck_projects_budget_nonnegative CHECK (budget>=0),
	CONSTRAINT ck_projects_dates_ordered CHECK (due>=start),
	CONSTRAINT [fk_projects_masterId_master_projects] FOREIGN KEY([masterId]) REFERENCES bia.master_projects (id),
	CONSTRAINT [fk_projects_createdById_users] FOREIGN KEY([createdById]) REFERENCES bia.users (id),
	CONSTRAINT [fk_projects_departmentId_departments] FOREIGN KEY([departmentId]) REFERENCES bia.departments (id)
);

CREATE INDEX [ix_projects_createdById] ON bia.projects ([createdById]);

CREATE INDEX [ix_projects_departmentId] ON bia.projects ([departmentId]);

CREATE INDEX [ix_projects_masterId] ON bia.projects ([masterId]);

CREATE TABLE bia.sessions (
	token VARCHAR(64) NOT NULL,
	user_id VARCHAR(36) NOT NULL,
	expires NUMERIC(18, 0) NOT NULL,
	CONSTRAINT pk_sessions PRIMARY KEY (token),
	CONSTRAINT fk_sessions_user_id_users FOREIGN KEY(user_id) REFERENCES bia.users (id)
);

CREATE INDEX ix_sessions_expires ON bia.sessions (expires);

CREATE INDEX ix_sessions_user_id ON bia.sessions (user_id);

CREATE TABLE bia.user_credentials (
	[userId] VARCHAR(36) NOT NULL,
	password_hash VARCHAR(255) NOT NULL,
	CONSTRAINT pk_user_credentials PRIMARY KEY ([userId]),
	CONSTRAINT [fk_user_credentials_userId_users] FOREIGN KEY([userId]) REFERENCES bia.users (id)
);

CREATE TABLE bia.audit_log (
	id VARCHAR(36) NOT NULL,
	[projectId] VARCHAR(36) NULL,
	[actorId] VARCHAR(36) NULL,
	actor NVARCHAR(80) NOT NULL,
	role VARCHAR(20) NOT NULL,
	action NVARCHAR(500) NOT NULL,
	at DATETIME2(6) NOT NULL,
	CONSTRAINT pk_audit_log PRIMARY KEY (id),
	CONSTRAINT [fk_audit_log_projectId_projects] FOREIGN KEY([projectId]) REFERENCES bia.projects (id),
	CONSTRAINT [fk_audit_log_actorId_users] FOREIGN KEY([actorId]) REFERENCES bia.users (id)
);

CREATE INDEX [ix_audit_log_actorId] ON bia.audit_log ([actorId]);

CREATE INDEX ix_audit_log_at ON bia.audit_log (at);

CREATE INDEX [ix_audit_log_projectId] ON bia.audit_log ([projectId]);

CREATE TABLE bia.project_baselines (
	id VARCHAR(36) NOT NULL,
	[projectId] VARCHAR(36) NOT NULL,
	version INTEGER NOT NULL,
	name NVARCHAR(80) NOT NULL,
	reason NVARCHAR(500) NOT NULL,
	[createdById] VARCHAR(36) NOT NULL,
	[createdBy] NVARCHAR(80) NOT NULL,
	[createdAt] DATETIME2(6) NOT NULL,
	title NVARCHAR(100) NOT NULL,
	start DATE NOT NULL,
	due DATE NOT NULL,
	CONSTRAINT pk_project_baselines PRIMARY KEY (id),
	CONSTRAINT [uq_project_baselines_projectId] UNIQUE ([projectId], version),
	CONSTRAINT ck_project_baselines_version_positive CHECK (version>=1),
	CONSTRAINT ck_project_baselines_dates_ordered CHECK (due>=start),
	CONSTRAINT [fk_project_baselines_projectId_projects] FOREIGN KEY([projectId]) REFERENCES bia.projects (id),
	CONSTRAINT [fk_project_baselines_createdById_users] FOREIGN KEY([createdById]) REFERENCES bia.users (id)
);

CREATE INDEX [ix_project_baselines_createdById] ON bia.project_baselines ([createdById]);

CREATE INDEX [ix_project_baselines_projectId] ON bia.project_baselines ([projectId]);

CREATE TABLE bia.project_days_off (
	[projectId] VARCHAR(36) NOT NULL,
	weekday INTEGER NOT NULL,
	CONSTRAINT pk_project_days_off PRIMARY KEY ([projectId], weekday),
	CONSTRAINT ck_project_days_off_weekday_valid CHECK (weekday>=0 AND weekday<=6),
	CONSTRAINT [fk_project_days_off_projectId_projects] FOREIGN KEY([projectId]) REFERENCES bia.projects (id)
);

CREATE TABLE bia.project_department_access (
	[projectId] VARCHAR(36) NOT NULL,
	[groupId] VARCHAR(36) NOT NULL,
	CONSTRAINT pk_project_department_access PRIMARY KEY ([projectId], [groupId]),
	CONSTRAINT [fk_project_department_access_projectId_projects] FOREIGN KEY([projectId]) REFERENCES bia.projects (id),
	CONSTRAINT [fk_project_department_access_groupId_departments] FOREIGN KEY([groupId]) REFERENCES bia.departments (id)
);

CREATE INDEX [ix_project_department_access_groupId] ON bia.project_department_access ([groupId]);

CREATE TABLE bia.purchase_orders (
	id VARCHAR(36) NOT NULL,
	[projectId] VARCHAR(36) NOT NULL,
	number NVARCHAR(60) COLLATE Latin1_General_100_CI_AS_SC NOT NULL,
	[vendorId] VARCHAR(36) NOT NULL,
	amount NUMERIC(18, 2) NOT NULL,
	date DATE NOT NULL,
	description NVARCHAR(300) NOT NULL,
	CONSTRAINT pk_purchase_orders PRIMARY KEY (id),
	CONSTRAINT ck_purchase_orders_amount_positive CHECK (amount>0),
	CONSTRAINT [fk_purchase_orders_projectId_projects] FOREIGN KEY([projectId]) REFERENCES bia.projects (id),
	CONSTRAINT uq_purchase_orders_number UNIQUE (number),
	CONSTRAINT [fk_purchase_orders_vendorId_vendors] FOREIGN KEY([vendorId]) REFERENCES bia.vendors (id)
);

CREATE INDEX [ix_purchase_orders_projectId] ON bia.purchase_orders ([projectId]);

CREATE INDEX [ix_purchase_orders_vendorId] ON bia.purchase_orders ([vendorId]);

CREATE TABLE bia.tasks (
	id VARCHAR(36) NOT NULL,
	[projectId] VARCHAR(36) NOT NULL,
	[parentId] VARCHAR(36) NULL,
	title NVARCHAR(180) NOT NULL,
	[assigneeId] VARCHAR(36) NULL,
	[resourceId] VARCHAR(36) NOT NULL,
	effort NUMERIC(12, 2) NOT NULL,
	start DATE NOT NULL,
	due DATE NOT NULL,
	progress INTEGER NOT NULL,
	blocked BIT NOT NULL,
	CONSTRAINT pk_tasks PRIMARY KEY (id),
	CONSTRAINT uq_tasks_id UNIQUE (id, [projectId]),
	CONSTRAINT fk_tasks_parent_same_project FOREIGN KEY([parentId], [projectId]) REFERENCES bia.tasks (id, [projectId]),
	CONSTRAINT ck_tasks_not_own_parent CHECK (parentId IS NULL OR parentId<>id),
	CONSTRAINT ck_tasks_progress_range CHECK (progress>=0 AND progress<=100),
	CONSTRAINT ck_tasks_effort_positive CHECK (effort>0),
	CONSTRAINT ck_tasks_dates_ordered CHECK (due>=start),
	CONSTRAINT ck_tasks_complete_not_blocked CHECK (progress<100 OR blocked=0),
	CONSTRAINT [fk_tasks_projectId_projects] FOREIGN KEY([projectId]) REFERENCES bia.projects (id),
	CONSTRAINT [fk_tasks_assigneeId_users] FOREIGN KEY([assigneeId]) REFERENCES bia.users (id),
	CONSTRAINT [fk_tasks_resourceId_resources] FOREIGN KEY([resourceId]) REFERENCES bia.resources (id)
);

CREATE INDEX [ix_tasks_assigneeId] ON bia.tasks ([assigneeId]);

CREATE INDEX ix_tasks_parent_project ON bia.tasks ([parentId], [projectId]);

CREATE INDEX [ix_tasks_projectId] ON bia.tasks ([projectId]);

CREATE INDEX [ix_tasks_resourceId] ON bia.tasks ([resourceId]);

CREATE TABLE bia.baseline_tasks (
	[baselineId] VARCHAR(36) NOT NULL,
	[taskId] VARCHAR(36) NOT NULL,
	[parentId] VARCHAR(36) NULL,
	title NVARCHAR(180) NOT NULL,
	start DATE NOT NULL,
	due DATE NOT NULL,
	effort NUMERIC(12, 2) NOT NULL,
	[isMilestone] BIT NOT NULL,
	CONSTRAINT pk_baseline_tasks PRIMARY KEY ([baselineId], [taskId]),
	CONSTRAINT ck_baseline_tasks_effort_positive CHECK (effort>0),
	CONSTRAINT ck_baseline_tasks_dates_ordered CHECK (due>=start),
	CONSTRAINT [fk_baseline_tasks_baselineId_project_baselines] FOREIGN KEY([baselineId]) REFERENCES bia.project_baselines (id),
	CONSTRAINT [fk_baseline_tasks_taskId_tasks] FOREIGN KEY([taskId]) REFERENCES bia.tasks (id),
	CONSTRAINT [fk_baseline_tasks_parentId_tasks] FOREIGN KEY([parentId]) REFERENCES bia.tasks (id)
);

CREATE INDEX [ix_baseline_tasks_parentId] ON bia.baseline_tasks ([parentId]);

CREATE INDEX [ix_baseline_tasks_taskId] ON bia.baseline_tasks ([taskId]);

CREATE TABLE bia.invoices (
	id VARCHAR(36) NOT NULL,
	[poId] VARCHAR(36) NOT NULL,
	number NVARCHAR(60) COLLATE Latin1_General_100_CI_AS_SC NOT NULL,
	amount NUMERIC(18, 2) NOT NULL,
	date DATE NOT NULL,
	due DATE NOT NULL,
	CONSTRAINT pk_invoices PRIMARY KEY (id),
	CONSTRAINT ck_invoices_amount_positive CHECK (amount>0),
	CONSTRAINT ck_invoices_dates_ordered CHECK (due>=date),
	CONSTRAINT [uq_invoices_poId] UNIQUE ([poId], number),
	CONSTRAINT [fk_invoices_poId_purchase_orders] FOREIGN KEY([poId]) REFERENCES bia.purchase_orders (id)
);

CREATE INDEX [ix_invoices_poId] ON bia.invoices ([poId]);

CREATE TABLE bia.progress_updates (
	id VARCHAR(36) NOT NULL,
	[taskId] VARCHAR(36) NOT NULL,
	progress INTEGER NOT NULL,
	note NVARCHAR(2000) NOT NULL,
	[authorId] VARCHAR(36) NULL,
	author NVARCHAR(80) NOT NULL,
	[createdAt] DATETIME2(6) NOT NULL,
	CONSTRAINT pk_progress_updates PRIMARY KEY (id),
	CONSTRAINT ck_progress_updates_progress_range CHECK (progress>=0 AND progress<=100),
	CONSTRAINT [fk_progress_updates_taskId_tasks] FOREIGN KEY([taskId]) REFERENCES bia.tasks (id),
	CONSTRAINT [fk_progress_updates_authorId_users] FOREIGN KEY([authorId]) REFERENCES bia.users (id)
);

CREATE INDEX [ix_progress_updates_authorId] ON bia.progress_updates ([authorId]);

CREATE INDEX [ix_progress_updates_createdAt] ON bia.progress_updates ([createdAt]);

CREATE INDEX [ix_progress_updates_taskId] ON bia.progress_updates ([taskId]);

CREATE TABLE bia.task_milestones (
	[taskId] VARCHAR(36) NOT NULL,
	CONSTRAINT pk_task_milestones PRIMARY KEY ([taskId]),
	CONSTRAINT [fk_task_milestones_taskId_tasks] FOREIGN KEY([taskId]) REFERENCES bia.tasks (id)
);

CREATE TABLE bia.task_predecessors (
	[taskId] VARCHAR(36) NOT NULL,
	[predecessorId] VARCHAR(36) NOT NULL,
	CONSTRAINT pk_task_predecessors PRIMARY KEY ([taskId], [predecessorId]),
	CONSTRAINT ck_task_predecessors_not_self CHECK (taskId<>predecessorId),
	CONSTRAINT [fk_task_predecessors_taskId_tasks] FOREIGN KEY([taskId]) REFERENCES bia.tasks (id),
	CONSTRAINT [fk_task_predecessors_predecessorId_tasks] FOREIGN KEY([predecessorId]) REFERENCES bia.tasks (id)
);

CREATE INDEX [ix_task_predecessors_predecessorId] ON bia.task_predecessors ([predecessorId]);

CREATE TABLE bia.invoice_payments (
	[invoiceId] VARCHAR(36) NOT NULL,
	reference NVARCHAR(100) NOT NULL,
	[paidDate] DATE NOT NULL,
	[recordedById] VARCHAR(36) NULL,
	CONSTRAINT pk_invoice_payments PRIMARY KEY ([invoiceId]),
	CONSTRAINT [fk_invoice_payments_invoiceId_invoices] FOREIGN KEY([invoiceId]) REFERENCES bia.invoices (id),
	CONSTRAINT [fk_invoice_payments_recordedById_users] FOREIGN KEY([recordedById]) REFERENCES bia.users (id)
);

CREATE INDEX [ix_invoice_payments_recordedById] ON bia.invoice_payments ([recordedById]);

INSERT INTO bia.roles (code, name) VALUES ('admin', N'Administrator');

INSERT INTO bia.roles (code, name) VALUES ('head', N'Vertical head');

INSERT INTO bia.roles (code, name) VALUES ('delegate', N'Delegate');

INSERT INTO bia.roles (code, name) VALUES ('finance', N'Finance');

INSERT INTO bia.roles (code, name) VALUES ('executive', N'Executive (scoped)');

INSERT INTO bia.roles (code, name) VALUES ('management', N'Management (read-only)');

INSERT INTO bia.departments (id, name, active) VALUES ('department-1', N'Digital & IT', 1);

INSERT INTO bia.departments (id, name, active) VALUES ('department-2', N'Warehouse', 1);

INSERT INTO bia.departments (id, name, active) VALUES ('department-3', N'Production', 1);

INSERT INTO bia.departments (id, name, active) VALUES ('department-4', N'Quality', 1);

INSERT INTO bia.departments (id, name, active) VALUES ('department-5', N'HR', 1);

INSERT INTO bia.departments (id, name, active) VALUES ('department-6', N'Engineering', 1);

INSERT INTO bia.resources (id, name, active) VALUES ('resource-1', N'Unassigned', 1);

INSERT INTO bia.master_projects (id, title, [primaryDepartmentId], owner, description) VALUES ('bia-digital-transformation', N'BIA Digital Transformation', 'department-1', N'Transformation office', N'Digital transformation programmes and workstreams.');

INSERT INTO bia.workspace (id, version) VALUES (1, 1);

INSERT INTO bia.schema_migrations (version, appliedAt) VALUES (8, SYSUTCDATETIME());

COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT>0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
-- Next: 02_runtime_permissions.sql, then create-admin through the Python CLI.
