# SQL Server data dictionary — schema v9

24 normalized tables in schema `bia`. Generated from the application model. All money is USD and `DECIMAL(18,2)`. No JSON business-data columns.

SQL identifiers are fixed by this model. Every table has a primary key; relationships use foreign keys. Dates are SQL DATE; UTC events are DATETIME2(6). VARCHAR(36) keys preserve existing IDs and accept new UUID strings. Keys never encode permissions.

## bia.departments

| Column | SQL type | Null? | Key / relationship |
|---|---|---|---|
| `id` | `VARCHAR(36)` | No | PK |
| `name` | `NVARCHAR(60) COLLATE Latin1_General_100_CI_AS_SC` | No | unique |
| `active` | `BIT` | No | — |

Constraints: `ck_departments_name_required`: `LEN(name)>0`
Unique tuple: `name`.
Indexes: Primary/unique key indexes only.

## bia.login_attempts

| Column | SQL type | Null? | Key / relationship |
|---|---|---|---|
| `key` | `VARCHAR(64)` | No | PK |
| `count` | `INTEGER` | No | — |
| `expires` | `NUMERIC(18, 0)` | No | — |

Constraints: `ck_login_attempts_count_positive`: `count>=1`
Indexes: `ix_login_attempts_expires` (expires)

## bia.resources

| Column | SQL type | Null? | Key / relationship |
|---|---|---|---|
| `id` | `VARCHAR(36)` | No | PK |
| `name` | `NVARCHAR(80) COLLATE Latin1_General_100_CI_AS_SC` | No | unique |
| `active` | `BIT` | No | — |

Constraints: `ck_resources_name_required`: `LEN(name)>0`
Unique tuple: `name`.
Indexes: Primary/unique key indexes only.

## bia.roles

| Column | SQL type | Null? | Key / relationship |
|---|---|---|---|
| `code` | `VARCHAR(20)` | No | PK |
| `name` | `NVARCHAR(80)` | No | — |

Constraints: `ck_roles_known_role`: `code IN ('admin','head','delegate','finance','executive','management')`
Indexes: Primary/unique key indexes only.

## bia.schema_migrations

| Column | SQL type | Null? | Key / relationship |
|---|---|---|---|
| `version` | `INTEGER` | No | PK |
| `appliedAt` | `DATETIME2(6)` | No | — |

Constraints: Primary / foreign / unique keys above.
Indexes: Primary/unique key indexes only.

## bia.vendors

| Column | SQL type | Null? | Key / relationship |
|---|---|---|---|
| `id` | `VARCHAR(36)` | No | PK |
| `name` | `NVARCHAR(100) COLLATE Latin1_General_100_CI_AS_SC` | No | unique |
| `active` | `BIT` | No | — |

Constraints: `ck_vendors_name_required`: `LEN(name)>0`
Unique tuple: `name`.
Indexes: Primary/unique key indexes only.

## bia.workspace

| Column | SQL type | Null? | Key / relationship |
|---|---|---|---|
| `id` | `INTEGER` | No | PK |
| `version` | `INTEGER` | No | — |

Constraints: `ck_workspace_singleton`: `id=1`; `ck_workspace_version_positive`: `version>=1`
Indexes: Primary/unique key indexes only.

## bia.master_projects

| Column | SQL type | Null? | Key / relationship |
|---|---|---|---|
| `id` | `VARCHAR(36)` | No | PK |
| `title` | `NVARCHAR(100) COLLATE Latin1_General_100_CI_AS_SC` | No | unique |
| `primaryDepartmentId` | `VARCHAR(36)` | Yes | FK → `bia.departments.id` |
| `owner` | `NVARCHAR(80)` | No | — |
| `description` | `NVARCHAR(1000)` | Yes | — |

Constraints: Primary / foreign / unique keys above.
Unique tuple: `title`.
Indexes: `ix_master_projects_primaryDepartmentId` (primaryDepartmentId)

## bia.users

| Column | SQL type | Null? | Key / relationship |
|---|---|---|---|
| `id` | `VARCHAR(36)` | No | PK |
| `email` | `NVARCHAR(254) COLLATE Latin1_General_100_CI_AS_SC` | No | unique |
| `name` | `NVARCHAR(80)` | No | — |
| `role` | `VARCHAR(20)` | No | FK → `bia.roles.code` |
| `departmentId` | `VARCHAR(36)` | No | FK → `bia.departments.id` |
| `active` | `BIT` | No | — |

Constraints: Primary / foreign / unique keys above.
Unique tuple: `email`.
Indexes: `ix_users_departmentId` (departmentId)

## bia.projects

| Column | SQL type | Null? | Key / relationship |
|---|---|---|---|
| `id` | `VARCHAR(36)` | No | PK |
| `masterId` | `VARCHAR(36)` | No | FK → `bia.master_projects.id` |
| `createdById` | `VARCHAR(36)` | Yes | FK → `bia.users.id` |
| `title` | `NVARCHAR(100)` | No | — |
| `departmentId` | `VARCHAR(36)` | No | FK → `bia.departments.id` |
| `owner` | `NVARCHAR(80)` | No | — |
| `budget` | `NUMERIC(18, 2)` | No | — |
| `start` | `DATE` | No | — |
| `due` | `DATE` | No | — |
| `description` | `NVARCHAR(1000)` | Yes | — |
| `color` | `VARCHAR(10)` | Yes | — |

Constraints: `ck_projects_dates_ordered`: `due>=start`; `ck_projects_budget_nonnegative`: `budget>=0`
Indexes: `ix_projects_createdById` (createdById), `ix_projects_departmentId` (departmentId), `ix_projects_masterId` (masterId)

## bia.sessions

| Column | SQL type | Null? | Key / relationship |
|---|---|---|---|
| `token` | `VARCHAR(64)` | No | PK |
| `user_id` | `VARCHAR(36)` | No | FK → `bia.users.id` |
| `expires` | `NUMERIC(18, 0)` | No | — |

Constraints: Primary / foreign / unique keys above.
Indexes: `ix_sessions_expires` (expires), `ix_sessions_user_id` (user_id)

## bia.user_credentials

| Column | SQL type | Null? | Key / relationship |
|---|---|---|---|
| `userId` | `VARCHAR(36)` | No | PK; FK → `bia.users.id` |
| `password_hash` | `VARCHAR(255)` | No | — |

Constraints: Primary / foreign / unique keys above.
Indexes: Primary/unique key indexes only.

## bia.audit_log

| Column | SQL type | Null? | Key / relationship |
|---|---|---|---|
| `id` | `VARCHAR(36)` | No | PK |
| `projectId` | `VARCHAR(36)` | Yes | FK → `bia.projects.id` |
| `actorId` | `VARCHAR(36)` | Yes | FK → `bia.users.id` |
| `actor` | `NVARCHAR(80)` | No | — |
| `role` | `VARCHAR(20)` | No | — |
| `action` | `NVARCHAR(500)` | No | — |
| `at` | `DATETIME2(6)` | No | — |

Constraints: Primary / foreign / unique keys above.
Indexes: `ix_audit_log_actorId` (actorId), `ix_audit_log_at` (at), `ix_audit_log_projectId` (projectId)

## bia.project_baselines

| Column | SQL type | Null? | Key / relationship |
|---|---|---|---|
| `id` | `VARCHAR(36)` | No | PK |
| `projectId` | `VARCHAR(36)` | No | FK → `bia.projects.id` |
| `version` | `INTEGER` | No | — |
| `name` | `NVARCHAR(80)` | No | — |
| `reason` | `NVARCHAR(500)` | No | — |
| `createdById` | `VARCHAR(36)` | No | FK → `bia.users.id` |
| `createdBy` | `NVARCHAR(80)` | No | — |
| `createdAt` | `DATETIME2(6)` | No | — |
| `title` | `NVARCHAR(100)` | No | — |
| `start` | `DATE` | No | — |
| `due` | `DATE` | No | — |

Constraints: `ck_project_baselines_version_positive`: `version>=1`; `ck_project_baselines_dates_ordered`: `due>=start`
Unique tuple: `projectId`, `version`.
Indexes: `ix_project_baselines_createdById` (createdById), `ix_project_baselines_projectId` (projectId)

## bia.project_days_off

| Column | SQL type | Null? | Key / relationship |
|---|---|---|---|
| `projectId` | `VARCHAR(36)` | No | PK; FK → `bia.projects.id` |
| `weekday` | `INTEGER` | No | PK |

Constraints: `ck_project_days_off_weekday_valid`: `weekday>=0 AND weekday<=6`
Indexes: Primary/unique key indexes only.

## bia.project_department_access

| Column | SQL type | Null? | Key / relationship |
|---|---|---|---|
| `projectId` | `VARCHAR(36)` | No | PK; FK → `bia.projects.id` |
| `groupId` | `VARCHAR(36)` | No | PK; FK → `bia.departments.id` |

Constraints: Primary / foreign / unique keys above.
Indexes: `ix_project_department_access_groupId` (groupId)

## bia.purchase_orders

| Column | SQL type | Null? | Key / relationship |
|---|---|---|---|
| `id` | `VARCHAR(36)` | No | PK |
| `projectId` | `VARCHAR(36)` | No | FK → `bia.projects.id` |
| `number` | `NVARCHAR(60) COLLATE Latin1_General_100_CI_AS_SC` | No | unique |
| `vendorId` | `VARCHAR(36)` | No | FK → `bia.vendors.id` |
| `amount` | `NUMERIC(18, 2)` | No | — |
| `date` | `DATE` | No | — |
| `description` | `NVARCHAR(300)` | No | — |

Constraints: `ck_purchase_orders_amount_positive`: `amount>0`
Unique tuple: `number`.
Indexes: `ix_purchase_orders_projectId` (projectId), `ix_purchase_orders_vendorId` (vendorId)

## bia.tasks

| Column | SQL type | Null? | Key / relationship |
|---|---|---|---|
| `id` | `VARCHAR(36)` | No | PK |
| `projectId` | `VARCHAR(36)` | No | FK → `bia.tasks.projectId`; FK → `bia.projects.id` |
| `parentId` | `VARCHAR(36)` | Yes | FK → `bia.tasks.id` |
| `title` | `NVARCHAR(180)` | No | — |
| `assigneeId` | `VARCHAR(36)` | Yes | FK → `bia.users.id` |
| `resourceId` | `VARCHAR(36)` | No | FK → `bia.resources.id` |
| `effort` | `NUMERIC(12, 2)` | No | — |
| `start` | `DATE` | No | — |
| `due` | `DATE` | No | — |
| `progress` | `INTEGER` | No | — |
| `blocked` | `BIT` | No | — |

Constraints: `ck_tasks_effort_positive`: `effort>0`; `ck_tasks_dates_ordered`: `due>=start`; `ck_tasks_complete_not_blocked`: `progress<100 OR blocked=0`; `ck_tasks_not_own_parent`: `parentId IS NULL OR parentId<>id`; `ck_tasks_progress_range`: `progress>=0 AND progress<=100`
Unique tuple: `id`, `projectId`.
Indexes: `ix_tasks_assigneeId` (assigneeId), `ix_tasks_parent_project` (parentId, projectId), `ix_tasks_projectId` (projectId), `ix_tasks_resourceId` (resourceId)

## bia.baseline_tasks

| Column | SQL type | Null? | Key / relationship |
|---|---|---|---|
| `baselineId` | `VARCHAR(36)` | No | PK; FK → `bia.project_baselines.id` |
| `taskId` | `VARCHAR(36)` | No | PK; FK → `bia.tasks.id` |
| `parentId` | `VARCHAR(36)` | Yes | FK → `bia.tasks.id` |
| `title` | `NVARCHAR(180)` | No | — |
| `start` | `DATE` | No | — |
| `due` | `DATE` | No | — |
| `effort` | `NUMERIC(12, 2)` | No | — |
| `isMilestone` | `BIT` | No | — |

Constraints: `ck_baseline_tasks_dates_ordered`: `due>=start`; `ck_baseline_tasks_effort_positive`: `effort>0`
Indexes: `ix_baseline_tasks_parentId` (parentId), `ix_baseline_tasks_taskId` (taskId)

## bia.invoices

| Column | SQL type | Null? | Key / relationship |
|---|---|---|---|
| `id` | `VARCHAR(36)` | No | PK |
| `poId` | `VARCHAR(36)` | No | FK → `bia.purchase_orders.id` |
| `number` | `NVARCHAR(60) COLLATE Latin1_General_100_CI_AS_SC` | No | — |
| `amount` | `NUMERIC(18, 2)` | No | — |
| `date` | `DATE` | No | — |
| `due` | `DATE` | No | — |

Constraints: `ck_invoices_dates_ordered`: `due>=date`; `ck_invoices_amount_positive`: `amount>0`
Unique tuple: `poId`, `number`.
Indexes: `ix_invoices_poId` (poId)

## bia.progress_updates

| Column | SQL type | Null? | Key / relationship |
|---|---|---|---|
| `id` | `VARCHAR(36)` | No | PK |
| `taskId` | `VARCHAR(36)` | No | FK → `bia.tasks.id` |
| `progress` | `INTEGER` | No | — |
| `note` | `NVARCHAR(2000)` | No | — |
| `authorId` | `VARCHAR(36)` | Yes | FK → `bia.users.id` |
| `author` | `NVARCHAR(80)` | No | — |
| `createdAt` | `DATETIME2(6)` | No | — |

Constraints: `ck_progress_updates_progress_range`: `progress>=0 AND progress<=100`
Indexes: `ix_progress_updates_authorId` (authorId), `ix_progress_updates_createdAt` (createdAt), `ix_progress_updates_taskId` (taskId)

## bia.task_milestones

| Column | SQL type | Null? | Key / relationship |
|---|---|---|---|
| `taskId` | `VARCHAR(36)` | No | PK; FK → `bia.tasks.id` |

Constraints: Primary / foreign / unique keys above.
Indexes: Primary/unique key indexes only.

## bia.task_predecessors

| Column | SQL type | Null? | Key / relationship |
|---|---|---|---|
| `taskId` | `VARCHAR(36)` | No | PK; FK → `bia.tasks.id` |
| `predecessorId` | `VARCHAR(36)` | No | PK; FK → `bia.tasks.id` |

Constraints: `ck_task_predecessors_not_self`: `taskId<>predecessorId`
Indexes: `ix_task_predecessors_predecessorId` (predecessorId)

## bia.invoice_payments

| Column | SQL type | Null? | Key / relationship |
|---|---|---|---|
| `invoiceId` | `VARCHAR(36)` | No | PK; FK → `bia.invoices.id` |
| `reference` | `NVARCHAR(100)` | No | — |
| `paidDate` | `DATE` | No | — |
| `recordedById` | `VARCHAR(36)` | Yes | FK → `bia.users.id` |

Constraints: Primary / foreign / unique keys above.
Indexes: `ix_invoice_payments_recordedById` (recordedById)

## Intentional exceptions and derived fields

- `master_projects.primaryDepartmentId` may be null only for migrated, previously unassigned masters. New/edit API commands require an active primary department. A DBA can make it NOT NULL after resolving all legacy rows.
- Legacy creator, author and audit identity links remain nullable when the original ID was not recorded. Never infer identity from a display name. New authenticated writes record these IDs.
- `owner` is an accountable lead/role display field, not a login or permission grant. Task ownership uses `assigneeId` → users.
- Audit `actor`/`role` and progress `author` deliberately preserve historical display snapshots even after an account rename.
- Task department is derived from its project. Invoice Paid/Unpaid status is derived from the existence of its settlement record. Summary progress, budget usage and management status are calculated, not duplicated as editable totals.
- A department is its own built-in access group: users.departmentId is membership; project_department_access is the many-to-many project grant. Management membership is users.role = management. No duplicate group membership table can drift out of sync.
- Full settlement only: invoice_payments has one row per invoice (invoiceId is PK and FK). No partial payments, multi-currency conversion or purchase-order line items are implied.
- Tables use no cascading deletes. The application deactivates accounts and lookups; it has no hard-delete business workflow.
