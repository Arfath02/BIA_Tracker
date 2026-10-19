-- BIA v11 -> v12: approved budget changes and invoice references.
-- Back up and stop the API. Run with the migration/DBA identity.
-- Additive: existing budgets, invoices and schedule baselines are preserved.
SET XACT_ABORT ON;
BEGIN TRY
BEGIN TRANSACTION;
IF EXISTS (SELECT 1 FROM bia.schema_migrations WHERE version>12)
 THROW 51000, 'Database is newer than this application.', 1;
IF EXISTS (SELECT 1 FROM bia.schema_migrations WHERE version=12)
BEGIN
 COMMIT TRANSACTION;
 PRINT 'Schema v12 already installed.';
 RETURN;
END;
IF NOT EXISTS (SELECT 1 FROM bia.schema_migrations WHERE version=11)
 THROW 51000, 'This script requires v11. Use deploy/migrate.py for older installations.', 1;

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
)

;
CREATE INDEX [ix_budget_change_requests_projectId] ON bia.budget_change_requests ([projectId]);

CREATE TABLE bia.invoice_budget_changes (
	[invoiceId] VARCHAR(36) NOT NULL, 
	[changeRequestId] VARCHAR(36) NOT NULL, 
	CONSTRAINT pk_invoice_budget_changes PRIMARY KEY ([invoiceId]), 
	CONSTRAINT [fk_invoice_budget_changes_invoiceId_invoices] FOREIGN KEY([invoiceId]) REFERENCES bia.invoices (id), 
	CONSTRAINT [fk_invoice_budget_changes_changeRequestId_budget_change_requests] FOREIGN KEY([changeRequestId]) REFERENCES bia.budget_change_requests (id)
)

;
CREATE INDEX [ix_invoice_budget_changes_changeRequestId] ON bia.invoice_budget_changes ([changeRequestId]);
INSERT INTO bia.schema_migrations(version,appliedAt) VALUES(12,SYSUTCDATETIME());
COMMIT TRANSACTION;
END TRY
BEGIN CATCH
 IF @@TRANCOUNT>0 ROLLBACK TRANSACTION;
 THROW;
END CATCH;
-- Reapply 02_runtime_permissions.sql before restarting the updated API.
