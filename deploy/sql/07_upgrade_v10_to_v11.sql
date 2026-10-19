-- BIA v10 -> v11. Back up the database and stop the API first.
-- Additive migration: existing consultant and travel rows are not rewritten.
-- Reapply 02_runtime_permissions.sql after upgrading.
SET XACT_ABORT ON;
BEGIN TRY
BEGIN TRANSACTION;
IF EXISTS (SELECT 1 FROM bia.schema_migrations WHERE version>11)
 THROW 51000, 'Database is newer than this application.', 1;
IF EXISTS (SELECT 1 FROM bia.schema_migrations WHERE version=11)
BEGIN
 COMMIT TRANSACTION;
 PRINT 'Schema v11 already installed.';
 RETURN;
END;
IF NOT EXISTS (SELECT 1 FROM bia.schema_migrations WHERE version=10)
 THROW 51000, 'This script requires v10. Use deploy/migrate.py for older installations.', 1;

CREATE TABLE bia.consultant_details (
	[consultantId] VARCHAR(36) NOT NULL, 
	designation NVARCHAR(100) NOT NULL, 
	CONSTRAINT pk_consultant_details PRIMARY KEY ([consultantId]), 
	CONSTRAINT [fk_consultant_details_consultantId_vendor_consultants] FOREIGN KEY([consultantId]) REFERENCES bia.vendor_consultants (id)
)

;

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
)

;

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
)

;
CREATE INDEX [ix_project_expenses_projectId] ON bia.project_expenses ([projectId]);
INSERT INTO bia.schema_migrations(version,appliedAt) VALUES(11,SYSUTCDATETIME());
COMMIT TRANSACTION;
END TRY
BEGIN CATCH
 IF @@TRANCOUNT>0 ROLLBACK TRANSACTION;
 THROW;
END CATCH;
