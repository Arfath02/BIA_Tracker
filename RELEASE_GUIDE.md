# BIA Project Tracker — complete source, API and SQL release

Release: 2026-10-18.1. SQL schema: v12 (35 normalized tables).

## What was repaired

The React interface and Python business layer supported seven commercial commands, but FastAPI's request model still rejected them with HTTP 422. Fixed commands: project_commercial, payment_term, consultant, trip, expense, change_request, change_decision. This affected the self-hosted Python installation; the Sites adapter used a separate command path.

New tests send actual HTTP requests through authentication, request validation, authorization, version checks and persistence. They cover create/edit of payment conditions, consultant designation, travel and expenses; finance approval outside project visibility; blocked self-approval/replay; linked PO/invoice/payment; unchanged budget after invoice/payment; rejected invalid input; and logout. A contract test compares the HTTP allowlist with Python command handlers to catch future omissions.

Includes the latest left-heading disclosure arrows, management drill-down, baseline/dependency/calendar scheduling, Gantt/export UI, financial approvals, JOD expenses, vendors and consultants. No live Site data, accounts, secrets or SQL credentials are included. The Sites review database and your SQL Server database are separate.

## Package map

- src/: full React source; production/: Python FastAPI, SQLAlchemy models and migrations.
- deploy/: Ubuntu Docker/Nginx configuration, setup tools and all SQL scripts.
- deploy/sql/01_schema.sql: full v12 fresh-install SQL, for an EMPTY dedicated database only.
- deploy/sql/02_runtime_permissions.sql: least-privilege runtime grants; edit only the approved database username if needed.
- deploy/sql/03_verify_runtime.sql: checks to execute as the runtime identity.
- deploy/sql/04…08: versioned SQL upgrades from v7 through v12.
- docs/database/: ER diagrams, data dictionary and database setup guide.
- docs/API_REFERENCE.md and docs/API_OPENAPI.json: Python routes and request schema, generated from this release.
- tests/: executable business, HTTP API, migration and DOM interaction checks.
- server/ and migrations/: separate Sites review adapter, not the Python SQL Server backend.

## Existing installation — update frontend AND API

Back up your database first. Extract into a new release folder. Preserve your private deploy/.env, TLS certificates and any trusted SQL CA certificates from the previous installation; do not overwrite them with examples. Run these commands from the extracted bia-tracker folder:

```sh
docker compose --env-file deploy/.env -f deploy/compose.yaml stop web api
docker compose --env-file deploy/.env -f deploy/compose.yaml build api web
```

If already on v12, this API repair requires no schema migration. If on an earlier supported schema, run `python3 deploy/migrate.py` with the separate migration identity. For a v11-only SQL upgrade, the DBA may instead run `deploy/sql/08_upgrade_v11_to_v12.sql` in the existing database. Do not run the fresh-install script on existing data. Reapply `02_runtime_permissions.sql` after a schema upgrade and run `03_verify_runtime.sql` as the runtime user.

```sh
docker compose --env-file deploy/.env -f deploy/compose.yaml up -d --force-recreate api web
docker compose --env-file deploy/.env -f deploy/compose.yaml ps
docker compose --env-file deploy/.env -f deploy/compose.yaml exec -T api python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/api/health').read().decode())"
```

Expected health JSON: `{"status":"ok","schemaVersion":12,"apiRelease":"2026-10-18.1"}`. A missing/older apiRelease indicates the old API image is still running. Hard-refresh your browser after both images are running, then sign in again. Use `deploy/README.md` for first installation, TLS and administrator creation; `python3 deploy/configure.py` prepares configuration without contacting SQL Server, and `sh deploy/setup.sh` is the guided operator installation.

TRUSTED_ORIGINS must exactly match the browser's HTTPS origin, including its port (for example https://tracker.biatextiles.co:8443 if that is the hostname/port you configure). Do not disable origin checks, TLS certificate validation or role checks to resolve an update error.

## Troubleshooting failed updates

| Result | Check |
| --- | --- |
| 401 | Sign in again; expired/revoked sessions cannot save. |
| 403 | Verify exact trusted origin and your role/project access. Management is read-only. |
| 409 | Refresh the workspace and review the latest values before resubmitting. Do not auto-retry a stale financial change. |
| 422 | Review validation text. If all newer commercial actions fail, check apiRelease and rebuild the API image. |
| 500 or unhealthy API | Check API logs, schema v12, SQL connectivity, runtime grants and trusted SQL TLS. Do not share passwords or connection strings in logs. |
| 502/504 or HTML response | Check Nginx/API container health and upstream connectivity. |

## Validation and remaining acceptance

Passed locally: 68 JavaScript business/export tests; 34 Python HTTP/business/normalization tests; 208 Sites API assertions; 58 DOM UI checks plus a central finance inbox scenario. The existing baseline UI test was updated to assert the current Gantt elements while preserving baseline/current/milestone checks. Build succeeded.

Python persistence/migration tests use disposable SQLite; SQL Server DDL is compiled and inspected. No live SQL Server, ODBC/TLS connection, runtime SQL permissions, Docker image build/startup or actual-browser rendering was tested in this environment. These must be verified on your staging server before production acceptance. This is not a security certification or a claim of complete OWASP coverage.

Run source checks locally after installing locked dependencies:

```sh
npm ci
npm run build
npm test
npm run test:integration
python3 -m venv .venv
. .venv/bin/activate
pip install -r production/requirements-test.txt
python -m pytest -q tests/test_python_api.py tests/test_commercial.py tests/test_sql_normalization.py
```

For server acceptance, use test accounts and a disposable project to create/edit a consultant, travel booking, expense and payment condition; submit and approve a budget request with different users; record its PO/invoice/payment; test a successor date change; and verify read-only management access. Keep production data out of automated test fixtures.
