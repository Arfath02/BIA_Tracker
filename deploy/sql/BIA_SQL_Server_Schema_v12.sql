-- BIA normalized schema v12. Generated from production/database.py.
-- NEW dedicated SQL Server database only. Select your database in SSMS first.
-- Existing v1-v11 installations: use python3 deploy/migrate.py instead.
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


CREATE TABLE bia.currency_codes (
	code VARCHAR(3) NOT NULL,
	name NVARCHAR(100) NOT NULL,
	digits INTEGER NOT NULL,
	CONSTRAINT pk_currency_codes PRIMARY KEY (code),
	CONSTRAINT ck_currency_codes_digits_range CHECK (digits>=0 AND digits<=4)
);

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
	budget NUMERIC(19, 4) NOT NULL,
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

CREATE TABLE bia.budget_change_requests (
	id VARCHAR(36) NOT NULL,
	[projectId] VARCHAR(36) NOT NULL,
	title NVARCHAR(100) NOT NULL,
	reason NVARCHAR(2000) NOT NULL,
	amount NUMERIC(19, 4) NOT NULL,
	status VARCHAR(10) NOT NULL,
	[requestedById] VARCHAR(36) NOT NULL,
	[requestedBy] NVARCHAR(100) NOT NULL,
	[requestedDate] DATE NOT NULL,
	[decidedById] VARCHAR(36) NULL,
	[decidedBy] NVARCHAR(100) NULL,
	[decisionDate] DATE NULL,
	[decisionNote] NVARCHAR(2000) NULL,
	[budgetBefore] NUMERIC(19, 4) NULL,
	[budgetAfter] NUMERIC(19, 4) NULL,
	CONSTRAINT pk_budget_change_requests PRIMARY KEY (id),
	CONSTRAINT ck_budget_change_requests_amount_positive CHECK (amount>0),
	CONSTRAINT ck_budget_change_requests_status_valid CHECK (status IN ('Pending','Approved','Rejected')),
	CONSTRAINT ck_budget_change_requests_review_valid CHECK ((status='Pending' AND decidedById IS NULL AND decisionDate IS NULL AND decisionNote IS NULL AND budgetBefore IS NULL AND budgetAfter IS NULL) OR (status IN ('Approved','Rejected') AND decidedById IS NOT NULL AND decidedById<>requestedById AND decisionDate IS NOT NULL AND decisionDate>=requestedDate AND decisionNote IS NOT NULL)),
	CONSTRAINT ck_budget_change_requests_budget_valid CHECK ((status='Approved' AND budgetBefore IS NOT NULL AND budgetAfter IS NOT NULL AND budgetBefore>=0 AND budgetAfter=budgetBefore+amount) OR (status<>'Approved' AND budgetBefore IS NULL AND budgetAfter IS NULL)),
	CONSTRAINT [fk_budget_change_requests_projectId_projects] FOREIGN KEY([projectId]) REFERENCES bia.projects (id),
	CONSTRAINT [fk_budget_change_requests_requestedById_users] FOREIGN KEY([requestedById]) REFERENCES bia.users (id),
	CONSTRAINT [fk_budget_change_requests_decidedById_users] FOREIGN KEY([decidedById]) REFERENCES bia.users (id)
);

CREATE INDEX [ix_budget_change_requests_projectId] ON bia.budget_change_requests ([projectId]);

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

CREATE TABLE bia.project_expenses (
	id VARCHAR(36) NOT NULL,
	[projectId] VARCHAR(36) NOT NULL,
	kind VARCHAR(20) NOT NULL,
	date DATE NOT NULL,
	[prNumber] NVARCHAR(60) COLLATE Latin1_General_100_CI_AS_SC NOT NULL,
	[amountJod] NUMERIC(19, 3) NOT NULL,
	remarks NVARCHAR(1000) NOT NULL,
	CONSTRAINT pk_project_expenses PRIMARY KEY (id),
	CONSTRAINT ck_project_expenses_kind_valid CHECK (kind IN ('spares','miscellaneous')),
	CONSTRAINT ck_project_expenses_amount_positive CHECK (amountJod>0),
	CONSTRAINT [uq_project_expenses_projectId] UNIQUE ([projectId], kind, [prNumber]),
	CONSTRAINT [fk_project_expenses_projectId_projects] FOREIGN KEY([projectId]) REFERENCES bia.projects (id)
);

CREATE INDEX [ix_project_expenses_projectId] ON bia.project_expenses ([projectId]);

CREATE TABLE bia.project_finance (
	[projectId] VARCHAR(36) NOT NULL,
	currency VARCHAR(3) NOT NULL,
	[usdRate] NUMERIC(18, 8) NOT NULL,
	[rateDate] DATE NULL,
	[vendorId] VARCHAR(36) NULL,
	CONSTRAINT pk_project_finance PRIMARY KEY ([projectId]),
	CONSTRAINT ck_project_finance_rate_positive CHECK (usdRate>0),
	CONSTRAINT ck_project_finance_usd_rate_one CHECK (currency<>'USD' OR usdRate=1),
	CONSTRAINT [fk_project_finance_projectId_projects] FOREIGN KEY([projectId]) REFERENCES bia.projects (id),
	CONSTRAINT fk_project_finance_currency_currency_codes FOREIGN KEY(currency) REFERENCES bia.currency_codes (code),
	CONSTRAINT [fk_project_finance_vendorId_vendors] FOREIGN KEY([vendorId]) REFERENCES bia.vendors (id)
);

CREATE INDEX [ix_project_finance_vendorId] ON bia.project_finance ([vendorId]);

CREATE TABLE bia.purchase_orders (
	id VARCHAR(36) NOT NULL,
	[projectId] VARCHAR(36) NOT NULL,
	number NVARCHAR(60) COLLATE Latin1_General_100_CI_AS_SC NOT NULL,
	[vendorId] VARCHAR(36) NOT NULL,
	amount NUMERIC(19, 4) NOT NULL,
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

CREATE TABLE bia.vendor_consultants (
	id VARCHAR(36) NOT NULL,
	[vendorId] VARCHAR(36) NOT NULL,
	[ownerProjectId] VARCHAR(36) NULL,
	name NVARCHAR(100) COLLATE Latin1_General_100_CI_AS_SC NOT NULL,
	active BIT NOT NULL,
	CONSTRAINT pk_vendor_consultants PRIMARY KEY (id),
	CONSTRAINT [uq_vendor_consultants_vendorId] UNIQUE ([vendorId], name),
	CONSTRAINT [fk_vendor_consultants_vendorId_vendors] FOREIGN KEY([vendorId]) REFERENCES bia.vendors (id),
	CONSTRAINT [fk_vendor_consultants_ownerProjectId_projects] FOREIGN KEY([ownerProjectId]) REFERENCES bia.projects (id)
);

CREATE INDEX [ix_vendor_consultants_ownerProjectId] ON bia.vendor_consultants ([ownerProjectId]);

CREATE INDEX [ix_vendor_consultants_vendorId] ON bia.vendor_consultants ([vendorId]);

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

CREATE TABLE bia.consultant_details (
	[consultantId] VARCHAR(36) NOT NULL,
	designation NVARCHAR(100) NOT NULL,
	CONSTRAINT pk_consultant_details PRIMARY KEY ([consultantId]),
	CONSTRAINT [fk_consultant_details_consultantId_vendor_consultants] FOREIGN KEY([consultantId]) REFERENCES bia.vendor_consultants (id)
);

CREATE TABLE bia.consultant_trips (
	id VARCHAR(36) NOT NULL,
	[projectId] VARCHAR(36) NOT NULL,
	[consultantId] VARCHAR(36) NOT NULL,
	start DATE NOT NULL,
	[end] DATE NOT NULL,
	[biaFlight] BIT NOT NULL,
	[biaAccommodation] BIT NOT NULL,
	[biaFood] BIT NOT NULL,
	[stayType] VARCHAR(20) NULL,
	[flightBooked] BIT NOT NULL,
	[flightCost] NUMERIC(19, 4) NULL,
	[bookedDate] DATE NULL,
	notes NVARCHAR(1000) NOT NULL,
	CONSTRAINT pk_consultant_trips PRIMARY KEY (id),
	CONSTRAINT ck_consultant_trips_dates_ordered CHECK ([end]>=start),
	CONSTRAINT ck_consultant_trips_stay_valid CHECK ((biaAccommodation=0 AND stayType IS NULL) OR (biaAccommodation=1 AND stayType IN ('campus','external'))),
	CONSTRAINT ck_consultant_trips_flight_valid CHECK ((flightBooked=0 AND flightCost IS NULL AND bookedDate IS NULL) OR (flightBooked=1 AND biaFlight=1 AND flightCost>0 AND bookedDate IS NOT NULL AND bookedDate<=start)),
	CONSTRAINT [fk_consultant_trips_projectId_projects] FOREIGN KEY([projectId]) REFERENCES bia.projects (id),
	CONSTRAINT [fk_consultant_trips_consultantId_vendor_consultants] FOREIGN KEY([consultantId]) REFERENCES bia.vendor_consultants (id)
);

CREATE INDEX [ix_consultant_trips_consultantId] ON bia.consultant_trips ([consultantId]);

CREATE INDEX [ix_consultant_trips_projectId] ON bia.consultant_trips ([projectId]);

CREATE TABLE bia.invoices (
	id VARCHAR(36) NOT NULL,
	[poId] VARCHAR(36) NOT NULL,
	number NVARCHAR(60) COLLATE Latin1_General_100_CI_AS_SC NOT NULL,
	amount NUMERIC(19, 4) NOT NULL,
	date DATE NOT NULL,
	due DATE NOT NULL,
	CONSTRAINT pk_invoices PRIMARY KEY (id),
	CONSTRAINT ck_invoices_amount_positive CHECK (amount>0),
	CONSTRAINT ck_invoices_dates_ordered CHECK (due>=date),
	CONSTRAINT [uq_invoices_poId] UNIQUE ([poId], number),
	CONSTRAINT [fk_invoices_poId_purchase_orders] FOREIGN KEY([poId]) REFERENCES bia.purchase_orders (id)
);

CREATE INDEX [ix_invoices_poId] ON bia.invoices ([poId]);

CREATE TABLE bia.payment_terms (
	id VARCHAR(36) NOT NULL,
	[projectId] VARCHAR(36) NOT NULL,
	title NVARCHAR(100) NOT NULL,
	amount NUMERIC(19, 4) NOT NULL,
	[trigger] VARCHAR(20) NOT NULL,
	[dueDate] DATE NULL,
	[milestoneId] VARCHAR(36) NULL,
	cancelled BIT NOT NULL,
	CONSTRAINT pk_payment_terms PRIMARY KEY (id),
	CONSTRAINT fk_terms_milestone_project FOREIGN KEY([milestoneId], [projectId]) REFERENCES bia.tasks (id, [projectId]),
	CONSTRAINT ck_payment_terms_amount_positive CHECK (amount>0),
	CONSTRAINT ck_payment_terms_valid_trigger CHECK (([trigger]='date' AND dueDate IS NOT NULL AND milestoneId IS NULL) OR ([trigger]='milestone' AND dueDate IS NULL AND milestoneId IS NOT NULL)),
	CONSTRAINT [fk_payment_terms_projectId_projects] FOREIGN KEY([projectId]) REFERENCES bia.projects (id)
);

CREATE INDEX [ix_payment_terms_projectId] ON bia.payment_terms ([projectId]);

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

CREATE TABLE bia.invoice_budget_changes (
	[invoiceId] VARCHAR(36) NOT NULL,
	[changeRequestId] VARCHAR(36) NOT NULL,
	CONSTRAINT pk_invoice_budget_changes PRIMARY KEY ([invoiceId]),
	CONSTRAINT [fk_invoice_budget_changes_invoiceId_invoices] FOREIGN KEY([invoiceId]) REFERENCES bia.invoices (id),
	CONSTRAINT [fk_invoice_budget_changes_changeRequestId_budget_change_requests] FOREIGN KEY([changeRequestId]) REFERENCES bia.budget_change_requests (id)
);

CREATE INDEX [ix_invoice_budget_changes_changeRequestId] ON bia.invoice_budget_changes ([changeRequestId]);

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

CREATE TABLE bia.invoice_terms (
	[invoiceId] VARCHAR(36) NOT NULL,
	[termId] VARCHAR(36) NOT NULL,
	CONSTRAINT pk_invoice_terms PRIMARY KEY ([invoiceId]),
	CONSTRAINT [fk_invoice_terms_invoiceId_invoices] FOREIGN KEY([invoiceId]) REFERENCES bia.invoices (id),
	CONSTRAINT [uq_invoice_terms_termId] UNIQUE ([termId]),
	CONSTRAINT [fk_invoice_terms_termId_payment_terms] FOREIGN KEY([termId]) REFERENCES bia.payment_terms (id)
);

CREATE TABLE bia.trip_costs (
	[tripId] VARCHAR(36) NOT NULL,
	[flightCostJod] NUMERIC(19, 3) NULL,
	[hotelBookedBy] VARCHAR(10) NULL,
	[hotelCostJod] NUMERIC(19, 3) NOT NULL,
	[visaCostJod] NUMERIC(19, 3) NOT NULL,
	CONSTRAINT pk_trip_costs PRIMARY KEY ([tripId]),
	CONSTRAINT ck_trip_costs_flight_positive CHECK (flightCostJod IS NULL OR flightCostJod>0),
	CONSTRAINT ck_trip_costs_costs_nonnegative CHECK (hotelCostJod>=0 AND visaCostJod>=0),
	CONSTRAINT ck_trip_costs_booker_valid CHECK (hotelBookedBy IS NULL OR hotelBookedBy IN ('bia','vendor')),
	CONSTRAINT ck_trip_costs_bia_hotel_only CHECK (hotelCostJod=0 OR hotelBookedBy='bia'),
	CONSTRAINT [fk_trip_costs_tripId_consultant_trips] FOREIGN KEY([tripId]) REFERENCES bia.consultant_trips (id)
);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('AED', N'UAE Dirham', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('AFN', N'Afghani', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('ALL', N'Lek', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('AMD', N'Armenian Dram', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('AOA', N'Kwanza', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('ARS', N'Argentine Peso', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('AUD', N'Australian Dollar', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('AWG', N'Aruban Florin', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('AZN', N'Azerbaijan Manat', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('BAM', N'Convertible Mark', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('BBD', N'Barbados Dollar', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('BDT', N'Taka', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('BHD', N'Bahraini Dinar', 3);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('BIF', N'Burundi Franc', 0);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('BMD', N'Bermudian Dollar', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('BND', N'Brunei Dollar', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('BOB', N'Boliviano', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('BOV', N'Mvdol', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('BRL', N'Brazilian Real', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('BSD', N'Bahamian Dollar', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('BTN', N'Ngultrum', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('BWP', N'Pula', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('BYN', N'Belarusian Ruble', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('BZD', N'Belize Dollar', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('CAD', N'Canadian Dollar', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('CDF', N'Congolese Franc', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('CHE', N'WIR Euro', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('CHF', N'Swiss Franc', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('CHW', N'WIR Franc', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('CLF', N'Unidad de Fomento', 4);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('CLP', N'Chilean Peso', 0);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('CNY', N'Yuan Renminbi', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('COP', N'Colombian Peso', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('COU', N'Unidad de Valor Real', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('CRC', N'Costa Rican Colon', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('CUP', N'Cuban Peso', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('CVE', N'Cabo Verde Escudo', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('CZK', N'Czech Koruna', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('DJF', N'Djibouti Franc', 0);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('DKK', N'Danish Krone', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('DOP', N'Dominican Peso', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('DZD', N'Algerian Dinar', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('EGP', N'Egyptian Pound', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('ERN', N'Nakfa', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('ETB', N'Ethiopian Birr', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('EUR', N'Euro', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('FJD', N'Fiji Dollar', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('FKP', N'Falkland Islands Pound', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('GBP', N'Pound Sterling', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('GEL', N'Lari', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('GHS', N'Ghana Cedi', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('GIP', N'Gibraltar Pound', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('GMD', N'Dalasi', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('GNF', N'Guinean Franc', 0);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('GTQ', N'Quetzal', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('GYD', N'Guyana Dollar', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('HKD', N'Hong Kong Dollar', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('HNL', N'Lempira', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('HTG', N'Gourde', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('HUF', N'Forint', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('IDR', N'Rupiah', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('ILS', N'New Israeli Sheqel', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('INR', N'Indian Rupee', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('IQD', N'Iraqi Dinar', 3);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('IRR', N'Iranian Rial', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('ISK', N'Iceland Krona', 0);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('JMD', N'Jamaican Dollar', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('JOD', N'Jordanian Dinar', 3);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('JPY', N'Yen', 0);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('KES', N'Kenyan Shilling', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('KGS', N'Som', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('KHR', N'Riel', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('KMF', N'Comorian Franc ', 0);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('KPW', N'North Korean Won', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('KRW', N'Won', 0);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('KWD', N'Kuwaiti Dinar', 3);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('KYD', N'Cayman Islands Dollar', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('KZT', N'Tenge', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('LAK', N'Lao Kip', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('LBP', N'Lebanese Pound', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('LKR', N'Sri Lanka Rupee', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('LRD', N'Liberian Dollar', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('LSL', N'Loti', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('LYD', N'Libyan Dinar', 3);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('MAD', N'Moroccan Dirham', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('MDL', N'Moldovan Leu', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('MGA', N'Malagasy Ariary', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('MKD', N'Denar', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('MMK', N'Kyat', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('MNT', N'Tugrik', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('MOP', N'Pataca', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('MRU', N'Ouguiya', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('MUR', N'Mauritius Rupee', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('MVR', N'Rufiyaa', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('MWK', N'Malawi Kwacha', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('MXN', N'Mexican Peso', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('MXV', N'Mexican Unidad de Inversion (UDI)', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('MYR', N'Malaysian Ringgit', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('MZN', N'Mozambique Metical', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('NAD', N'Namibia Dollar', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('NGN', N'Naira', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('NIO', N'Cordoba Oro', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('NOK', N'Norwegian Krone', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('NPR', N'Nepalese Rupee', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('NZD', N'New Zealand Dollar', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('OMR', N'Rial Omani', 3);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('PAB', N'Balboa', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('PEN', N'Sol', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('PGK', N'Kina', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('PHP', N'Philippine Peso', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('PKR', N'Pakistan Rupee', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('PLN', N'Zloty', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('PYG', N'Guarani', 0);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('QAR', N'Qatari Rial', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('RON', N'Romanian Leu', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('RSD', N'Serbian Dinar', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('RUB', N'Russian Ruble', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('RWF', N'Rwanda Franc', 0);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('SAR', N'Saudi Riyal', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('SBD', N'Solomon Islands Dollar', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('SCR', N'Seychelles Rupee', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('SDG', N'Sudanese Pound', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('SEK', N'Swedish Krona', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('SGD', N'Singapore Dollar', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('SHP', N'Saint Helena Pound', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('SLE', N'Leone', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('SOS', N'Somali Shilling', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('SRD', N'Surinam Dollar', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('SSP', N'South Sudanese Pound', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('STN', N'Dobra', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('SVC', N'El Salvador Colon', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('SYP', N'Syrian Pound', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('SZL', N'Lilangeni', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('THB', N'Baht', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('TJS', N'Somoni', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('TMT', N'Turkmenistan New Manat', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('TND', N'Tunisian Dinar', 3);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('TOP', N'Pa’anga', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('TRY', N'Turkish Lira', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('TTD', N'Trinidad and Tobago Dollar', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('TWD', N'New Taiwan Dollar', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('TZS', N'Tanzanian Shilling', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('UAH', N'Hryvnia', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('UGX', N'Uganda Shilling', 0);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('USD', N'US Dollar', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('USN', N'US Dollar (Next day)', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('UYI', N'Uruguay Peso en Unidades Indexadas (UI)', 0);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('UYU', N'Peso Uruguayo', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('UYW', N'Unidad Previsional', 4);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('UZS', N'Uzbekistan Sum', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('VED', N'Bolívar Soberano', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('VES', N'Bolívar Soberano', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('VND', N'Dong', 0);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('VUV', N'Vatu', 0);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('WST', N'Tala', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('XAD', N'Arab Accounting Dinar', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('XAF', N'CFA Franc BEAC', 0);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('XCD', N'East Caribbean Dollar', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('XCG', N'Caribbean Guilder', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('XOF', N'CFA Franc BCEAO', 0);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('XPF', N'CFP Franc', 0);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('YER', N'Yemeni Rial', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('ZAR', N'Rand', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('ZMW', N'Zambian Kwacha', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('ZWG', N'Zimbabwe Gold', 2);

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

INSERT INTO bia.schema_migrations (version, appliedAt) VALUES (12, SYSUTCDATETIME());

COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT>0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
-- Next: 02_runtime_permissions.sql, then create-admin through the Python CLI.
