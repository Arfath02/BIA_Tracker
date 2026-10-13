-- Back up the dedicated BIA database, stop the API, then run as the migration identity.
-- Preserves all dates/baselines; existing subprojects initially have no weekly days off.
SET XACT_ABORT ON;
BEGIN TRY
BEGIN TRANSACTION;
DECLARE @result int;
EXEC @result=sys.sp_getapplock @Resource=N'BIA schema v7 migration', @LockMode='Exclusive', @LockOwner='Transaction', @LockTimeout=0;
IF @result<0 THROW 51000, 'Another migration is running.', 1;
IF NOT EXISTS (SELECT 1 FROM bia.schema_migrations WHERE version=8) OR EXISTS (SELECT 1 FROM bia.schema_migrations WHERE version>8)
    THROW 51000, 'This script requires schema v8. Use the application migration for other versions.', 1;
CREATE TABLE bia.project_days_off (
    [projectId] VARCHAR(36) NOT NULL,
    [weekday] INTEGER NOT NULL,
    CONSTRAINT pk_project_days_off PRIMARY KEY ([projectId],[weekday]),
    CONSTRAINT fk_project_days_off_projectId_projects FOREIGN KEY ([projectId]) REFERENCES bia.projects(id),
    CONSTRAINT ck_project_days_off_weekday_valid CHECK ([weekday]>=0 AND [weekday]<=6)
);
INSERT INTO bia.schema_migrations(version,appliedAt) VALUES (9,SYSUTCDATETIME());
COMMIT;
END TRY
BEGIN CATCH
IF @@TRANCOUNT>0 ROLLBACK;
THROW;
END CATCH;
-- Reapply 02_runtime_permissions.sql before starting the new API.
