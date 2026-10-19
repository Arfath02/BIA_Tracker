# Current schema v12

See [budget approvals and Gantt](../BUDGET_CHANGES_GANTT.md). Fresh databases use `01_schema.sql`; v11 uses `08_upgrade_v11_to_v12.sql`; older versions use the Python migrator. Reapply current runtime grants. Historical notes follow.

# Current schema v11

See [expense migration and data treatment](../EXPENSES.md). Fresh installations use `01_schema.sql`; v10 uses `07_upgrade_v10_to_v11.sql`; earlier versions use `deploy/migrate.py`. Reapply current runtime grants.

# Current schema v10

The application requires v10 (30 normalized tables). Follow [../COMMERCIAL.md](../COMMERCIAL.md) for the preserving upgrade and runtime grants. Fresh installs use 01_schema.sql. Older release notes follow.

# Current schema v9

The current application requires v9 (24 normalized tables). Follow [../SCHEDULING.md](../SCHEDULING.md) for the preserving v8 upgrade and reapply runtime permissions. Fresh installs use the regenerated 01_schema.sql. Historical v8/v7 notes follow.

# Schema v8 update

The current model contains 23 tables. For an existing normalized v7 database, use the preserving Python migration or `deploy/sql/04_upgrade_v7_to_v8.sql`, then reapply runtime permissions. See `docs/BASELINES.md`. The fresh-install script now creates v8 directly. The v7 normalization notes below remain historical background for v1–v6 upgrades.

# BIA SQL Server database setup

The server edition now stores application data in **20 related tables in the `bia` schema**. `workspace` contains only a concurrency counter. There is no JSON column holding projects, tasks or financial records. The Python API joins the tables and returns the existing React interface's data format.

## What is separated

| Area | Physical tables |
|---|---|
| Master data | `departments`, `vendors`, `resources`, `roles` |
| Identity and access | `users`, `user_credentials`, `sessions`, `login_attempts`, `project_department_access` |
| Planning | `master_projects`, `projects`, `tasks`, `task_predecessors` |
| Progress and history | `progress_updates`, `audit_log` |
| Financial records | `purchase_orders`, `invoices`, `invoice_payments` |
| Operations | `workspace`, `schema_migrations` |

Each has a primary key. Project sharing and predecessor tables have composite primary keys, preventing duplicate links. Foreign keys prevent orphan records. Unique constraints prevent duplicate department/vendor/resource names, account emails, master names, PO numbers, and invoice numbers within one PO. Lookup uniqueness uses an explicit case-insensitive SQL Server collation.

Open **BIA_ERD.html** for the offline diagrams; **DATA_DICTIONARY.md** lists every column, type, relationship, constraint and index. Mermaid and Graphviz source files are included for editing.

## Recommended connection

The connection is **React browser → HTTPS/Nginx → Python FastAPI → encrypted ODBC → SQL Server**. Only Python has the SQL credential. Do not put a SQL connection string in JavaScript, expose SQL Server to browsers, or give application users the runtime SQL password.

Use a supported, patched SQL Server release and a dedicated BIA database. The schema uses standard tables, DATE, DATETIME2 and foreign keys; no JSON, CLR, xp_cmdshell, linked server or special enterprise feature is required. Deployment must be tested against your actual SQL Server version and collation.

## New installation: choose one schema installation method

**Recommended: supplied setup wizard.** From the extracted source root:

```bash
python3 deploy/configure.py
bash deploy/setup.sh
```

This builds the containers, checks connectivity, prompts for a separate DDL identity, installs schema v7, and pauses for your DBA to grant runtime permissions. It then creates the first administrator through a password prompt. No default password exists.

**Alternative: DBA creates the tables in SSMS first.**

1. Create/select your dedicated database, for example `BIA_Transformation`. Do not run this in an ERP, HRMS, `master`, or unrelated database.
2. Review and run `deploy/sql/01_schema.sql` using the DDL identity. It creates the `bia` schema, all 20 tables, constraints, indexes, fixed roles, initial departments, the Unassigned resource, the original Digital Transformation master, and the version records. No accounts or transactions are seeded. It refuses an existing application schema.
3. Map the runtime SQL login to a database user using your organization's normal account process. Review `deploy/sql/02_runtime_permissions.sql`, replace `[bia_runtime]` if necessary, and execute it as DBA.
4. Connect as the actual runtime login and run `deploy/sql/03_verify_runtime.sql`. All `passed` values must be 1; unexpected permissions and untrusted constraints result sets must be empty.
5. Run the same configuration/setup commands above. The migration sees v7 and leaves the installed records intact. Create the administrator when prompted.

The configuration wizard writes an owner-only `deploy/.env`. SQL TLS certificate verification is required: `Encrypt=yes` and `TrustServerCertificate=no`, with ODBC Driver 18. Place your trusted internal CA's public `.crt` files in `deploy/ca-certificates/` before building if needed. Do not bypass certificate validation to make a connection work.

## Upgrade from a prior downloaded installation

1. Back up SQL Server and verify that the backup can be restored. Preserve the old source/image, `deploy/.env` and TLS files. Stop all API/web instances, including any older deployment using this database.
2. Extract the new source, restore your private configuration, then run:

```bash
docker compose --env-file deploy/.env -f deploy/compose.yaml stop api web
docker compose --env-file deploy/.env -f deploy/compose.yaml build
python3 deploy/migrate.py
```

3. The operator-only migration copies recognized v1–v6 `dbo` records into new normalized `bia` tables, inside a transaction. It preserves IDs, password hashes, workspace version, grants, task dependencies, notes, audit history and financial totals. It verifies entity IDs, totals and paid-invoice identity before recording v7. It never guesses missing creators/authors, promotes users, or grants new project access.
4. Old login sessions are not copied. Everyone signs in again. Legacy `dbo` tables remain untouched for DBA comparison/recovery. Old vendor/resource names no longer in a catalog become separate inactive values rather than being guessed to match a renamed business.
5. Custom legacy columns/constraints, triggers or SQL row-security policies require DBA review and stop automatic migration. Extra indexes, reporting views, stored procedures and other extensions are not copied. Ambiguous names, orphan references, invalid dates, inconsistent task departments, invalid payment records, populated unversioned target tables, or newer schema versions stop the migration. Resolve the reported data issue on a backed-up test copy first; do not disable constraints or delete data to force it through. IDs longer than 36 characters or values beyond the documented column limits also need DBA reconciliation.
6. Apply **02_runtime_permissions.sql**. This is required: it grants only the necessary `bia` access and denies app access to retained legacy `dbo` tables. Check **03_verify_runtime.sql** using the runtime login.
7. Restart and perform the acceptance checks below:

```bash
docker compose --env-file deploy/.env -f deploy/compose.yaml up -d
```

After new writes have occurred in v7, the legacy copy is no longer current. Do not point an old app at it as a shortcut rollback. Stop writes and restore the verified pre-upgrade backup plus the matching old application, or perform a DBA-reviewed reconciliation. This release does not ship a destructive automatic downgrade.

## Acceptance before operational use

- Confirm a new administrator login; create test Head, Delegate, Finance and Management accounts.
- Verify a department-scoped user cannot read another project's tasks, money, audit or exports by changing IDs or calling the API directly.
- Verify Management reads department → project → task progress across all masters and every business write is denied.
- Create a master with primary department, a subproject, tasks/subtasks and predecessors. Rename the department, vendor and resource; IDs and links must remain stable.
- Save simultaneous edits from two browsers; stale workspace versions must return 409 without partial changes.
- Create a PO/invoice and record full settlement; overspending, duplicate settlement and invalid dates must be rejected.
- Change a user's role/department, disable them, or reset their password; prior sessions must stop working.
- Verify TLS, firewall, runtime SQL permissions, trusted/enabled constraints, backup restoration, log handling, patching and expected workload. Run a deployment-specific security assessment.

## Important boundaries

The Sites review prototype uses its own private D1 snapshot storage and accounts. It is not connected to your SQL Server. This release normalizes the **downloaded Python/SQL Server edition**; it does not export live Sites records or apply SQL to your infrastructure.

Department groups are represented by `users.departmentId` plus `project_department_access`. Management is a fixed role. Extra membership tables are unnecessary while each user has one home department. If you later need multi-department membership, multiple roles, partial payments or PO line items, those require deliberate schema and permission changes, not storing lists inside a column.

Cross-row budget totals, dependency cycles, predecessor completion, date containment, last-administrator safeguards and row visibility are enforced by the API. The database independently enforces keys, scalar bounds, date order and same-project task parents. Do not let staff edit business tables directly in SSMS or through Access linked tables; that bypasses API authorization and workflow rules. Use Access only for an explicitly approved restricted reporting connection, with separate credentials and views designed for its audience.
