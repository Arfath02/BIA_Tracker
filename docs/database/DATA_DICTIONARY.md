# SQL Server data dictionary — schema v12

35 normalized tables in schema `bia`. Generated from the application model. Transaction amounts use project currency and `DECIMAL(19,4)`; reporting uses an explicit USD rate. No JSON business-data columns.

SQL identifiers are fixed by this model. Every table has a primary key; relationships use foreign keys. Dates are SQL DATE; UTC events are DATETIME2(6). VARCHAR(36) keys preserve existing IDs and accept new UUID strings. Keys never encode permissions.

## bia.currency_codes

| Column | SQL type | Null? | Key / relationship |
|---|---|---|---|
| `code` | `VARCHAR(3)` | No | PK |
| `name` | `NVARCHAR(100)` | No | — |
| `digits` | `INTEGER` | No | — |

Constraints: `ck_currency_codes_digits_range`: `digits>=0 AND digits<=4`
Indexes: Primary/unique key indexes only.

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

Constraints: `ck_workspace_version_positive`: `version>=1`; `ck_workspace_singleton`: `id=1`
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
| `budget` | `NUMERIC(19, 4)` | No | — |
| `start` | `DATE` | No | — |
| `due` | `DATE` | No | — |
| `description` | `NVARCHAR(1000)` | Yes | — |
| `color` | `VARCHAR(10)` | Yes | — |

Constraints: `ck_projects_budget_nonnegative`: `budget>=0`; `ck_projects_dates_ordered`: `due>=start`
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

## bia.budget_change_requests

| Column | SQL type | Null? | Key / relationship |
|---|---|---|---|
| `id` | `VARCHAR(36)` | No | PK |
| `projectId` | `VARCHAR(36)` | No | FK → `bia.projects.id` |
| `title` | `NVARCHAR(100)` | No | — |
| `reason` | `NVARCHAR(2000)` | No | — |
| `amount` | `NUMERIC(19, 4)` | No | — |
| `status` | `VARCHAR(10)` | No | — |
| `requestedById` | `VARCHAR(36)` | No | FK → `bia.users.id` |
| `requestedBy` | `NVARCHAR(100)` | No | — |
| `requestedDate` | `DATE` | No | — |
| `decidedById` | `VARCHAR(36)` | Yes | FK → `bia.users.id` |
| `decidedBy` | `NVARCHAR(100)` | Yes | — |
| `decisionDate` | `DATE` | Yes | — |
| `decisionNote` | `NVARCHAR(2000)` | Yes | — |
| `budgetBefore` | `NUMERIC(19, 4)` | Yes | — |
| `budgetAfter` | `NUMERIC(19, 4)` | Yes | — |

Constraints: `ck_budget_change_requests_review_valid`: `(status='Pending' AND decidedById IS NULL AND decisionDate IS NULL AND decisionNote IS NULL AND budgetBefore IS NULL AND budgetAfter IS NULL) OR (status IN ('Approved','Rejected') AND decidedById IS NOT NULL AND decidedById<>requestedById AND decisionDate IS NOT NULL AND decisionDate>=requestedDate AND decisionNote IS NOT NULL)`; `ck_budget_change_requests_amount_positive`: `amount>0`; `ck_budget_change_requests_budget_valid`: `(status='Approved' AND budgetBefore IS NOT NULL AND budgetAfter IS NOT NULL AND budgetBefore>=0 AND budgetAfter=budgetBefore+amount) OR (status<>'Approved' AND budgetBefore IS NULL AND budgetAfter IS NULL)`; `ck_budget_change_requests_status_valid`: `status IN ('Pending','Approved','Rejected')`
Indexes: `ix_budget_change_requests_projectId` (projectId)

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

## bia.project_expenses

| Column | SQL type | Null? | Key / relationship |
|---|---|---|---|
| `id` | `VARCHAR(36)` | No | PK |
| `projectId` | `VARCHAR(36)` | No | FK → `bia.projects.id` |
| `kind` | `VARCHAR(20)` | No | — |
| `date` | `DATE` | No | — |
| `prNumber` | `NVARCHAR(60) COLLATE Latin1_General_100_CI_AS_SC` | No | — |
| `amountJod` | `NUMERIC(19, 3)` | No | — |
| `remarks` | `NVARCHAR(1000)` | No | — |

Constraints: `ck_project_expenses_amount_positive`: `amountJod>0`; `ck_project_expenses_kind_valid`: `kind IN ('spares','miscellaneous')`
Unique tuple: `projectId`, `kind`, `prNumber`.
Indexes: `ix_project_expenses_projectId` (projectId)

## bia.project_finance

| Column | SQL type | Null? | Key / relationship |
|---|---|---|---|
| `projectId` | `VARCHAR(36)` | No | PK; FK → `bia.projects.id` |
| `currency` | `VARCHAR(3)` | No | FK → `bia.currency_codes.code` |
| `usdRate` | `NUMERIC(18, 8)` | No | — |
| `rateDate` | `DATE` | Yes | — |
| `vendorId` | `VARCHAR(36)` | Yes | FK → `bia.vendors.id` |

Constraints: `ck_project_finance_usd_rate_one`: `currency<>'USD' OR usdRate=1`; `ck_project_finance_rate_positive`: `usdRate>0`
Indexes: `ix_project_finance_vendorId` (vendorId)

## bia.purchase_orders

| Column | SQL type | Null? | Key / relationship |
|---|---|---|---|
| `id` | `VARCHAR(36)` | No | PK |
| `projectId` | `VARCHAR(36)` | No | FK → `bia.projects.id` |
| `number` | `NVARCHAR(60) COLLATE Latin1_General_100_CI_AS_SC` | No | unique |
| `vendorId` | `VARCHAR(36)` | No | FK → `bia.vendors.id` |
| `amount` | `NUMERIC(19, 4)` | No | — |
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

## bia.vendor_consultants

| Column | SQL type | Null? | Key / relationship |
|---|---|---|---|
| `id` | `VARCHAR(36)` | No | PK |
| `vendorId` | `VARCHAR(36)` | No | FK → `bia.vendors.id` |
| `ownerProjectId` | `VARCHAR(36)` | Yes | FK → `bia.projects.id` |
| `name` | `NVARCHAR(100) COLLATE Latin1_General_100_CI_AS_SC` | No | — |
| `active` | `BIT` | No | — |

Constraints: Primary / foreign / unique keys above.
Unique tuple: `vendorId`, `name`.
Indexes: `ix_vendor_consultants_ownerProjectId` (ownerProjectId), `ix_vendor_consultants_vendorId` (vendorId)

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

Constraints: `ck_baseline_tasks_effort_positive`: `effort>0`; `ck_baseline_tasks_dates_ordered`: `due>=start`
Indexes: `ix_baseline_tasks_parentId` (parentId), `ix_baseline_tasks_taskId` (taskId)

## bia.consultant_details

| Column | SQL type | Null? | Key / relationship |
|---|---|---|---|
| `consultantId` | `VARCHAR(36)` | No | PK; FK → `bia.vendor_consultants.id` |
| `designation` | `NVARCHAR(100)` | No | — |

Constraints: Primary / foreign / unique keys above.
Indexes: Primary/unique key indexes only.

## bia.consultant_trips

| Column | SQL type | Null? | Key / relationship |
|---|---|---|---|
| `id` | `VARCHAR(36)` | No | PK |
| `projectId` | `VARCHAR(36)` | No | FK → `bia.projects.id` |
| `consultantId` | `VARCHAR(36)` | No | FK → `bia.vendor_consultants.id` |
| `start` | `DATE` | No | — |
| `end` | `DATE` | No | — |
| `biaFlight` | `BIT` | No | — |
| `biaAccommodation` | `BIT` | No | — |
| `biaFood` | `BIT` | No | — |
| `stayType` | `VARCHAR(20)` | Yes | — |
| `flightBooked` | `BIT` | No | — |
| `flightCost` | `NUMERIC(19, 4)` | Yes | — |
| `bookedDate` | `DATE` | Yes | — |
| `notes` | `NVARCHAR(1000)` | No | — |

Constraints: `ck_consultant_trips_flight_valid`: `(flightBooked=0 AND flightCost IS NULL AND bookedDate IS NULL) OR (flightBooked=1 AND biaFlight=1 AND flightCost>0 AND bookedDate IS NOT NULL AND bookedDate<=start)`; `ck_consultant_trips_dates_ordered`: `[end]>=start`; `ck_consultant_trips_stay_valid`: `(biaAccommodation=0 AND stayType IS NULL) OR (biaAccommodation=1 AND stayType IN ('campus','external'))`
Indexes: `ix_consultant_trips_consultantId` (consultantId), `ix_consultant_trips_projectId` (projectId)

## bia.invoices

| Column | SQL type | Null? | Key / relationship |
|---|---|---|---|
| `id` | `VARCHAR(36)` | No | PK |
| `poId` | `VARCHAR(36)` | No | FK → `bia.purchase_orders.id` |
| `number` | `NVARCHAR(60) COLLATE Latin1_General_100_CI_AS_SC` | No | — |
| `amount` | `NUMERIC(19, 4)` | No | — |
| `date` | `DATE` | No | — |
| `due` | `DATE` | No | — |

Constraints: `ck_invoices_amount_positive`: `amount>0`; `ck_invoices_dates_ordered`: `due>=date`
Unique tuple: `poId`, `number`.
Indexes: `ix_invoices_poId` (poId)

## bia.payment_terms

| Column | SQL type | Null? | Key / relationship |
|---|---|---|---|
| `id` | `VARCHAR(36)` | No | PK |
| `projectId` | `VARCHAR(36)` | No | FK → `bia.projects.id`; FK → `bia.tasks.projectId` |
| `title` | `NVARCHAR(100)` | No | — |
| `amount` | `NUMERIC(19, 4)` | No | — |
| `trigger` | `VARCHAR(20)` | No | — |
| `dueDate` | `DATE` | Yes | — |
| `milestoneId` | `VARCHAR(36)` | Yes | FK → `bia.tasks.id` |
| `cancelled` | `BIT` | No | — |

Constraints: `ck_payment_terms_amount_positive`: `amount>0`; `ck_payment_terms_valid_trigger`: `([trigger]='date' AND dueDate IS NOT NULL AND milestoneId IS NULL) OR ([trigger]='milestone' AND dueDate IS NULL AND milestoneId IS NOT NULL)`
Indexes: `ix_payment_terms_projectId` (projectId)

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

## bia.invoice_budget_changes

| Column | SQL type | Null? | Key / relationship |
|---|---|---|---|
| `invoiceId` | `VARCHAR(36)` | No | PK; FK → `bia.invoices.id` |
| `changeRequestId` | `VARCHAR(36)` | No | FK → `bia.budget_change_requests.id` |

Constraints: Primary / foreign / unique keys above.
Indexes: `ix_invoice_budget_changes_changeRequestId` (changeRequestId)

## bia.invoice_payments

| Column | SQL type | Null? | Key / relationship |
|---|---|---|---|
| `invoiceId` | `VARCHAR(36)` | No | PK; FK → `bia.invoices.id` |
| `reference` | `NVARCHAR(100)` | No | — |
| `paidDate` | `DATE` | No | — |
| `recordedById` | `VARCHAR(36)` | Yes | FK → `bia.users.id` |

Constraints: Primary / foreign / unique keys above.
Indexes: `ix_invoice_payments_recordedById` (recordedById)

## bia.invoice_terms

| Column | SQL type | Null? | Key / relationship |
|---|---|---|---|
| `invoiceId` | `VARCHAR(36)` | No | PK; FK → `bia.invoices.id` |
| `termId` | `VARCHAR(36)` | No | FK → `bia.payment_terms.id`; unique |

Constraints: Primary / foreign / unique keys above.
Unique tuple: `termId`.
Indexes: Primary/unique key indexes only.

## bia.trip_costs

| Column | SQL type | Null? | Key / relationship |
|---|---|---|---|
| `tripId` | `VARCHAR(36)` | No | PK; FK → `bia.consultant_trips.id` |
| `flightCostJod` | `NUMERIC(19, 3)` | Yes | — |
| `hotelBookedBy` | `VARCHAR(10)` | Yes | — |
| `hotelCostJod` | `NUMERIC(19, 3)` | No | — |
| `visaCostJod` | `NUMERIC(19, 3)` | No | — |

Constraints: `ck_trip_costs_costs_nonnegative`: `hotelCostJod>=0 AND visaCostJod>=0`; `ck_trip_costs_booker_valid`: `hotelBookedBy IS NULL OR hotelBookedBy IN ('bia','vendor')`; `ck_trip_costs_flight_positive`: `flightCostJod IS NULL OR flightCostJod>0`; `ck_trip_costs_bia_hotel_only`: `hotelCostJod=0 OR hotelBookedBy='bia'`
Indexes: Primary/unique key indexes only.

## Intentional exceptions and derived fields

- `master_projects.primaryDepartmentId` may be null only for migrated, previously unassigned masters. New/edit API commands require an active primary department. A DBA can make it NOT NULL after resolving all legacy rows.
- Legacy creator, author and audit identity links remain nullable when the original ID was not recorded. Never infer identity from a display name. New authenticated writes record these IDs.
- `owner` is an accountable lead/role display field, not a login or permission grant. Task ownership uses `assigneeId` → users.
- Audit `actor`/`role` and progress `author` deliberately preserve historical display snapshots even after an account rename.
- Task department is derived from its project. Invoice Paid/Unpaid status is derived from the existence of its settlement record. Summary progress, budget usage and management status are calculated, not duplicated as editable totals.
- A department is its own built-in access group: users.departmentId is membership; project_department_access is the many-to-many project grant. Management membership is users.role = management. No duplicate group membership table can drift out of sync.
- Full settlement only: invoice_payments has one row per invoice (invoiceId is PK and FK). Full settlement per invoice; installment conditions use separate invoices. Project rates convert to USD for management reporting.
- Tables use no cascading deletes. The application deactivates accounts and lookups; it has no hard-delete business workflow.
