-- DBA only. Preserving upgrade from normalized schema v7 to v8.
-- Stop the API, back up the database, then run in its dedicated database.
SET XACT_ABORT ON;
BEGIN TRY
BEGIN TRANSACTION;
DECLARE @lockResult int;
EXEC @lockResult=sys.sp_getapplock @Resource=N'BIA schema v7 migration', @LockMode='Exclusive', @LockOwner='Transaction', @LockTimeout=0;
IF @lockResult<0 THROW 51000, 'Another migration is running.', 1;
IF NOT EXISTS(SELECT 1 FROM bia.schema_migrations WHERE version=7) OR EXISTS(SELECT 1 FROM bia.schema_migrations WHERE version>7)
    THROW 51001, 'This script requires schema v7. For other versions use the Python migration.', 1;



CREATE TABLE bia.task_milestones (
	[taskId] VARCHAR(36) NOT NULL,
	CONSTRAINT pk_task_milestones PRIMARY KEY ([taskId]),
	CONSTRAINT [fk_task_milestones_taskId_tasks] FOREIGN KEY([taskId]) REFERENCES bia.tasks (id)
)

;


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
)

;

CREATE INDEX [ix_project_baselines_projectId] ON bia.project_baselines ([projectId]);

CREATE INDEX [ix_project_baselines_createdById] ON bia.project_baselines ([createdById]);


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
)

;

CREATE INDEX [ix_baseline_tasks_taskId] ON bia.baseline_tasks ([taskId]);

CREATE INDEX [ix_baseline_tasks_parentId] ON bia.baseline_tasks ([parentId]);

INSERT INTO bia.schema_migrations(version,appliedAt) VALUES(8,SYSUTCDATETIME());
COMMIT;
END TRY
BEGIN CATCH
IF @@TRANCOUNT>0 ROLLBACK;
THROW;
END CATCH;
-- Reapply 02_runtime_permissions.sql; validate with 03_verify_runtime.sql.
-- Baselines are not invented for existing projects. Save their approved plan in the app.
