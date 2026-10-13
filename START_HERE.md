# Latest release: automatic scheduling (schema v9)

Read [docs/SCHEDULING.md](docs/SCHEDULING.md) for calendars, successor scheduling and the preserving SQL upgrade. Use the current schema v9 scripts; the older release notes below are historical.

# BIA Project Portfolio — install on your server

This package contains the complete React frontend, Python FastAPI backend, Microsoft SQL Server schema and Ubuntu hosting configuration. You own and can modify the source. No Sites account is required to run the Ubuntu version.

Database documentation: [SQL setup and migration](docs/database/DATABASE_SETUP.md), [offline ER diagrams](docs/database/BIA_ERD.html), [every table and column](docs/database/DATA_DICTIONARY.md), and [security review](docs/SECURITY_REVIEW.md). For a fresh database, your DBA can run `deploy/sql/01_schema.sql` directly in SSMS; existing installations use the preserving Python migration.

## 1. Have these ready

- An Ubuntu server with Docker Engine, the Docker Compose plugin and Python 3.
- A **dedicated** SQL Server database named `BIA_Transformation` (or your preferred name), reachable from the Ubuntu host. Do not use your ERP or HRMS database.
- Two SQL logins mapped to users in that database: a migration/operator login with DDL permissions and a runtime login with only the permissions in `deploy/sql/02_runtime_permissions.sql`.
- An internal HTTPS name, for example `https://bia.company.local:8443`, and its certificate files `fullchain.pem` and `privkey.pem` in a directory on the Ubuntu host. Port 8443 avoids taking over an existing website on 443.
- A SQL Server TLS certificate trusted by the container and matching the SQL DNS name. If your organization uses a private CA, place its **public root/intermediate certificates** (`.crt`, never private keys) in `deploy/ca-certificates/` before building.

The API image installs Microsoft ODBC Driver 18 and accepts its license during build. Review this and the container sources according to your IT policy.

## 2. Extract and configure

Extract the ZIP on the Ubuntu server, enter the `bia-tracker` directory and run:

```bash
python3 deploy/configure.py
bash deploy/setup.sh
```

The configuration wizard asks for the SQL server, TCP port, database, runtime login/password, application HTTPS origin, listen IP and TLS directory. Password input is hidden, special characters are encoded, and the resulting `deploy/.env` has owner-only permissions. It refuses to overwrite an existing configuration.

The setup script builds both containers, checks database connectivity, and prompts for the migration login/password. It then installs the schema without dropping existing records. When prompted, have your DBA apply `deploy/sql/02_runtime_permissions.sql` and add the runtime SQL user to that role. Continue to create the first administrator and start the app.

The listen IP defaults to `127.0.0.1`. To serve the approved internal network, configure the server's LAN IP and restrict access with your firewall/VPN. Set DNS to that server. The HTTPS origin must exactly match the URL users open, including any nonstandard port.

**SQL connectivity is configured only on your server. Credentials never go in React or this ZIP.**

## 3. Sign in and manage the application

**Multiple master projects:** after administrator sign-in, choose **New master project** at the top of the workspace. Enter its name, required primary department, accountable lead and purpose. The primary department uses the editable department list in Admin portal → Master data. The new master is selected automatically. Choose **New subproject** to begin planning its work. The **Master project** dropdown switches every dashboard, task and financial view; **All master projects** shows a consolidated portfolio and individual master summary cards. **Edit master** changes its name, primary department, lead and purpose without changing child records.

BIA Digital Transformation and its existing records remain together, with Digital & IT as its initial primary department (or that department’s renamed name). Other older masters show “Not set” until an administrator selects their primary department. The primary department identifies programme accountability; subprojects may have different departments. Project visibility still follows the existing creator, head, task-assignment and explicit group grants. The primary department is shown in the master selector, portfolio cards and CSV reports. Master progress is effort-weighted from leaf tasks; master budget and financial totals come from linked subprojects, POs and invoices. Predecessors may cross subprojects within one master, but cannot cross masters. Departments, resource/vendor lists, account roles and the workspace audit remain shared; master selection filters reports after the API has restricted the data to projects the signed-in user may access.

**Management dashboard and group:** open **Admin portal → Management group**. Choose **Add management account**, or select an existing account and **Review membership change**, then save it with the **Management (read-only)** role. Keep the person's home department. The built-in group starts with no members; existing Executive accounts are not automatically promoted. Administrators can also assign the role through Users & roles. Reassign any open tasks before converting a contributor to Management.

Management users land directly on **Management dashboard**. It opens with **All master projects** selected. Each department card shows effort-weighted progress, project counts, completed projects, at-risk projects, deliverables and budget. Click **department → project name → task breakdown**. Project rows include their master project and its primary department. The task view displays nested subtasks, calculated summary progress, status, resource/owner, dates, predecessors and latest update notes. Breadcrumbs return to the department or portfolio. Search projects or select a master scope to narrow the report.

Department totals use the **delivery department on each subproject**, combining work across masters. Each subproject contributes once. The master primary department remains accountable for the programme and is shown separately. Progress weights only leaf tasks by planned hours; projects with no task plan are flagged instead of treated as complete. Risk is raised for blocked work, incomplete overdue tasks or an overdue project. The dashboard refreshes with the workspace every 45 seconds while visible; use Refresh workspace for an immediate refresh.

Management can read every current and future project, task, update and financial record, across all departments. The server denies all project, finance, catalog, account and sharing changes from that role. Members can change their own password and sign out. To remove membership, change their role or disable their account; either change revokes their sessions. The group is part of this app, not a Microsoft 365 or Sites sharing group. Hosting remains private; no invitations or sharing changes are made automatically.

Open your configured HTTPS URL and use the administrator you created in the terminal.

- **Admin portal → Master data → Departments / Vendors / Resource teams**: choose **Add value** or **Edit**. Uncheck **Available for new records** to deactivate a value.
- Department renames update master primary departments, subprojects, tasks and accounts. Vendor/resource renames update linked display names while SQL foreign-key IDs remain stable. Audit and author display snapshots retain their original wording.
- **Admin portal → Users & roles**: add accounts, change names/roles/departments, disable accounts or reset passwords. Role/department/email changes and resets revoke the affected account's sessions. Reassign open tasks before moving an active account to another department or incompatible role.
- **Admin portal → Department groups → Manage access**: select the departments that need each subproject. Every department automatically has a group; its active accounts are the members. Group access includes project tasks, updates and financials. Removing a group grant removes that route of access on the next request.
- **Admin portal → Audit log**: review who changed what and when.
- Create subprojects, tasks, POs and invoices in the main workspace. Their records supply the corresponding dropdown lists. Permission roles and computed statuses follow fixed rules.

Administrators and Management (read-only) members see all projects. Other accounts see projects they created, projects in their department when they are a vertical head, projects with tasks assigned to them, and projects explicitly shared with their department group. Dashboards, exports, tasks, POs, invoices, updates and project activity are filtered on the server. Finance and executive accounts also need a project access grant; their role alone does not give portfolio-wide visibility. Heads can create subprojects for their department; only administrators create master projects. Assign a first project before a new head begins working. Role permissions still control all writes: sharing a project does not let a delegate edit the plan or an executive change data. Shared dropdown catalogs remain workspace-wide. No invitation or password email is sent. Share initial credentials using your organization's approved channel. Users change passwords from their profile.

Production begins with no sample projects, transactions or accounts. It installs six editable departments and an “Unassigned” resource. Add vendors and resource teams before creating POs/tasks.

## Useful commands

Run from the extracted project root. Always include `--env-file`; Compose uses it for the HTTPS port and TLS path as well as the API configuration.

```bash
# Status and logs (review before sharing logs externally)
docker compose --env-file deploy/.env -f deploy/compose.yaml ps
docker compose --env-file deploy/.env -f deploy/compose.yaml logs --tail=100 api web

# Stop containers; SQL data stays on your existing SQL Server
docker compose --env-file deploy/.env -f deploy/compose.yaml down

# Start again
docker compose --env-file deploy/.env -f deploy/compose.yaml up -d

# Check only the configured SQL connection
docker compose --env-file deploy/.env -f deploy/compose.yaml run --rm api python -m production.manage check-db

# Upgrade using the new extracted source, preserving deploy/.env and TLS files
# Take a database backup first. Stop the application during schema changes.
docker compose --env-file deploy/.env -f deploy/compose.yaml stop api web
docker compose --env-file deploy/.env -f deploy/compose.yaml build
python3 deploy/migrate.py
# Have the DBA apply the supplied runtime grants if upgrading from an older schema.
docker compose --env-file deploy/.env -f deploy/compose.yaml up -d
```

Version 7 replaces text-based relationships with 20 normalized tables in the `bia` schema, copies prior dbo records without dropping the old tables, and separates credentials and invoice settlements. Follow **docs/database/DATABASE_SETUP.md** for the exact fresh-install or preserving-upgrade path and rollback limitations. Reapply the supplied runtime permissions before starting the new API; everyone signs in again after migration. The database scripts and documentation are part of this source package.

## What is included / what still needs your environment

`src/`: React UI, including the admin portal. `production/`: Python API and normalized SQL tables. `deploy/`: configuration wizard, installer, SQL permissions, Docker and Nginx. `tests/`: business, API and component checks. `server/`: the separate adapter for the private Sites review.

The private review Site and your SQL Server installation use separate databases. This ZIP contains source and explicitly labelled sample fixtures, **not an export of live Site users, passwords or workspace data**. Accounts and operational data are created on your server.

The code is validated locally. A real SQL Server connection, Ubuntu container startup, certificates, backups and production acceptance still need testing in your environment. See `deploy/README.md` and `VALIDATION.md` for the exact scope and checks. No BIA server or external system was accessed or modified while preparing this package.


## Login and responsive dashboards — October 2026

Opening the application without a valid app session shows only the sign-in page. Enter the account created by your administrator. A valid existing session resumes your dashboard; sign out from your profile to switch accounts. First-administrator setup is available only on an uninitialized private review Site. On your own Python/SQL Server installation, use the documented `production.manage create-admin` command.

After login, Management members open the all-department management dashboard with department → project → task drill-down. Administrators, heads, delegates, finance and executive users start on an overview of all master projects they are permitted to see. Finance users open Financial control from the navigation. The admin portal appears only for administrators. Department grants control project visibility; roles and assignments control which actions are available. Empty access shows an empty portfolio, with no example project data.

On phones and tablets, use the menu button in the top bar. Close navigation with its close button, the backdrop or Escape. Project/task/finance/user tables become labelled record cards on narrow screens. Search remains available on mobile. Forms stack into one column; the timeline retains its own horizontal scroll area. These changes also ship in the React production build and require no database migration.


## Baseline release — schema v8

See **docs/BASELINES.md** for saving immutable versioned schedules, marking key milestones, revising dates with reasons, and reviewing delays in progress/breakdown/timeline charts. SQL Server now has 23 tables. Existing v7 installations require the preserving v8 migration and updated runtime grants; this release adds three tables and keeps existing plans. Never run the fresh-install script on existing data.
