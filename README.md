# Latest full-source package — 2026-10-18.1

See [RELEASE_GUIDE.md](RELEASE_GUIDE.md). This release repairs seven missing Python HTTP mutation actions and adds authenticated HTTP regression coverage. SQL remains v12.

# Dashboard controls, exports and Finance approval inbox

See [usage and access controls](docs/CONTROLS_EXPORTS_APPROVALS.md). SQL schema remains v12; deploy the updated frontend and API together.

# Budget change requests and Gantt — latest release

See [workflow, charts and v12 upgrade](docs/BUDGET_CHANGES_GANTT.md).

# BIA Project Portfolio

A private portfolio workspace with multiple master projects, a read-only management dashboard, task execution and financial control.

See [consultant fixes, JOD expenses and v11 upgrade](docs/EXPENSES.md).

See [commercial features and historical v10 upgrade](docs/COMMERCIAL.md) for currencies, payment reminders and consultant travel.

## Install on your server

Start with [START_HERE.md](START_HERE.md). It includes a guided SQL connection wizard, Ubuntu installer and administrator instructions.

## Review URL

https://bia-transformation-control.classicfashi-1604.chatgpt.site

The Site is owner-private. Sign in with the owning ChatGPT account. Select **Set up your account** to establish the initial application administrator. There are no predefined credentials. App accounts are independent of the Sites visitor allowlist; creating an account does not invite a person or broaden Site access.

All initial project schedules, progress, budgets, vendors, POs and invoices are **illustrative data**, not current BIA records. Sample workstreams reflect BIA's transformation context only. The existing BIA Digital Transformation master retains its six initial illustrative subprojects. Administrators can create additional master projects for programmes outside the digital portfolio.

## What works

- **Management dashboard:** cumulative delivery-department progress across all masters → project names and status → tasks and nested subtasks with status, owners, dates and latest updates. Includes master scope, search, breadcrumbs and responsive views.
- **Management group:** a built-in, initially empty group managed in Admin portal. Assign the Management (read-only) role for full portfolio visibility with server-enforced rejection of business changes. Existing Executive users retain their scoped access.

- Multiple master projects → subprojects → tasks → nested subtasks. Create/edit master names, required primary departments, accountable leads and descriptions; select a master or use All master projects for a consolidated dashboard. Financials, updates and exports follow the selected master. Primary departments appear on master summaries and exports and follow department renames.
- Master → subprojects → tasks → nested subtasks. Summaries are computed from leaf-task planned hours; no double counting.
- Planned dates, resources, departments, finish-to-start predecessors within the same master, dependency/parent cycle checks, and timeline views.
- Progress updates with notes and blocking reasons. A successor cannot start until all predecessor deliverables finish. Incomplete work is never rounded up to 100%.
- Shared server persistence, account sign-in, admin/head/delegate/finance/executive permissions, account revocation and password changes.
- Department groups derive membership from account departments. Administrators manage explicit project sharing. Management members see all projects in read-only mode. Other users see only projects they create, manage as a department head, have tasks assigned in, or receive through a group. API responses, dashboards, financials, exports and activity are filtered. Heads create/plan department subprojects and delegates; delegates update only assigned tasks. Finance/executive roles require project visibility grants too.
- Department and project filters, search, project drill-down, management RAG status, activity history, CSV reports.
- Currency-specific project budgets, purchase orders, linked invoices, full invoice settlement records and payment references. USD management totals use explicit project reporting rates. Date/milestone payment conditions and consultant visits are maintained in project Finance and Travel tabs. Commitments cannot exceed the subproject budget; cumulative invoices cannot exceed their PO. No payments are initiated.
- Admin portal for department, vendor and resource master data; account creation/editing, role/department changes, disabling and password resets; audit history. Inactive values are preserved for historical records.
- Version checks reject stale writes. All successful business changes have a server-authored activity entry.

## Two deployment environments

| Layer | Private Sites review | Ubuntu deployment package |
|---|---|---|
| Frontend | React 19 + Vite | Same React app, production edition |
| API | Cloudflare Worker adapter | Python FastAPI |
| Database | Managed D1 with versioned review state | Normalized Microsoft SQL Server tables via SQLAlchemy + ODBC 18 |
| Identity | Sites private gate + app sessions | App sessions behind internal HTTPS; optional enterprise SSO to be integrated separately |
| Password storage | PBKDF2-SHA256, WebCrypto 100k iterations | Argon2id (64 MiB, 3 passes, parallelism 2) |
| Audit | Review activity capped at 1,000 business entries | Append-only application audit and progress-update tables |
| TLS | Managed by Sites | Nginx reverse proxy with organization-trusted certificate |

The Sites runtime is not an Ubuntu/Python/SQL Server host. No BIA server, database, DNS, ERP, mailbox or other existing external system has been modified. The private review and production backend are separate adapters for the same frontend API contract.

## Local review and tests

```sh
npm ci
npm run build
node scripts/preview.mjs
```

Open http://127.0.0.1:8787. The local D1 store is separate from the hosted Site.

```sh
npm test
npm run test:api
npm run test:admin
npm run test:masters
npm run test:access
npm run test:management
npm run test:ui
python -m venv .venv
. .venv/bin/activate
pip install -r production/requirements.lock -r production/requirements-test.txt
python -m pytest tests/test_python_api.py tests/test_sql_normalization.py -q
```

The API integration suite runs an isolated in-memory Worker/D1 environment. Python API tests run SQLite locally and compile the schema for the SQL Server dialect; they do not prove execution against a real SQL Server.

## Ubuntu deployment

See [deployment guide](deploy/README.md). Schema creation and initial administrator creation are explicit operator actions. Production startup performs no DDL and does not load sample data. No credentials are in source control.

## Release evidence and remaining gates

See [validation record](VALIDATION.md). This is a working review prototype and an implementation baseline for controlled production deployment, not a completed production acceptance or security certification. Before operational use, complete actual SQL Server integration tests, end-to-end browser acceptance, backup/restore validation, credential/identity review, dependency scanning, and load testing for the intended number of users. The review stores a bounded workspace snapshot; use the normalized Python/SQL Server backend for operational scale.

Prototype design decisions: multiple master portfolios, USD reporting, finish-to-start dependencies, calendar-day dates in Asia/Amman, full invoice payments, and no destructive delete action. Editing a PO or project baseline after approval, automated schedule recalculation, partial payments, attachments and approval routing are not implemented in this first version.

References: [Sites hosting](https://learn.chatgpt.com/docs/sites), [D1 configuration](https://developers.cloudflare.com/workers/wrangler/configuration/), [FastAPI password security](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/).


## Normalized SQL Server release (v7)

The Python backend uses 20 linked tables in the bia schema, including dedicated departments, vendors, resources, credentials and invoice settlements. See [database setup](docs/database/DATABASE_SETUP.md), [offline ERD](docs/database/BIA_ERD.html), [data dictionary](docs/database/DATA_DICTIONARY.md) and [security review](docs/SECURITY_REVIEW.md). The private Sites prototype remains a separate D1 review deployment. No live prototype data or SQL credentials are included.
