# Validation record — normalized SQL Server schema v7

Date: 2026-10-01. This release adds a normalized relational storage adapter and preserving migration, generated SQL/ER documentation, and targeted security improvements. It retains the multi-master portfolio, primary department, department groups and Management drill-down.

## Passed

- 37 Node business/access/report tests, including CSV formula neutralization and whitespace/control-character cases.
- Worker/D1 API suites: 26 core checks, 50 administration checks, 63 access checks, 26 master-project checks, and 43 Management checks. Each uses isolated test data, never live Site records.
- 60 JSDOM interactive checks using the real Worker API: account setup, subproject/task/subtask creation, progress/dependencies/rollups, PO/invoice/payment validation, admin forms and Management department → project → task navigation.
- 22 Python tests against disposable SQLite databases with **foreign keys enabled**, plus compilation of all 20 tables and their indexes to Microsoft SQL Server DDL. Coverage includes protected reads, every Management write denial, department/assignment isolation, stale edits and finance rollback, reset/revocation, missing-origin/body-size rejection, password throttling, safe error responses, lookup renames preserving IDs, separate password hashes, linked update authors, and relational scalar/FK constraints.
- Preserving v1 and v6 migration tests: original IDs, master links, missing legacy identities, password hashes, financial totals, invoice settlements and source records; repeat initialization is idempotent; old sessions remain only in the legacy copy. Ambiguous catalog names and customized columns/constraints stop automatic upgrade.
- React/Worker review build and React production-edition build (`VITE_EDITION=production`). Installer Bash syntax and diff checks.
- Full `npm audit` (including development dependencies): zero known advisories after updating Vite/esbuild and test-tool HTTP/WebSocket overrides. Python audit: zero known advisories in the 19 resolved production packages. Reports are in `docs/NPM_AUDIT.json` and `docs/DEPENDENCY_AUDIT.json`; the Python image uses `requirements.lock`.
- Four generated ERD SVG views were raster-rendered for inspection; planning, access and finance views were visually inspected. Self-contained offline HTML contains the diagrams without external scripts or network requests. Mermaid, Graphviz and full data dictionary sources are included.

## Architecture and migration boundary

The production model has 20 tables in schema `bia`, with primary keys, foreign keys, indexes, native DATE/DATETIME2 columns, decimal money and separate master data, credentials and settlements. `workspace` stores only a version counter. The API uses parameterized SQL and per-command authorization; it computes joined display fields and roll-up values for React. Migration is an operator action, not a web request. Runtime object grants and read-only verification SQL are supplied.

The original owner-private Sites review is a separate Worker/D1 implementation with snapshot storage and separate accounts. It is not connected to SQL Server. This release does not export or import live Site data, change sharing, invite users or change any BIA external system. The source ZIP excludes live account data, passwords, SQL connection strings, local databases, dependency directories and build caches.

## Not verified here

- Execution of the generated SQL or migration on a real Microsoft SQL Server. Its actual TLS/certificate trust, collation, SQL permissions, transaction locking and deployment-specific data still need acceptance on a restored test database.
- Ubuntu/Docker startup, built container scans, actual server/firewall/HTTPS configuration, backup restoration, load or penetration testing.
- Pixel-level web application layout in a supported real browser. JSDOM verifies interactions, not browser rendering.
- Enterprise SSO/MFA, direct Access reporting permissions or integrations with external business systems; none are implemented by this change.

Point-in-time dependency checks do not guarantee absence of vulnerabilities. This is a tested implementation baseline, not production certification. See `docs/SECURITY_REVIEW.md`, `docs/database/DATABASE_SETUP.md` and `START_HERE.md` for the controls, limitations and operator acceptance steps.


## Login-first and responsive release — 2026-10-11

- `npm test`: 37 domain, access, management, master and CSV checks.
- API suites: 26 core, 63 access, 43 management and 26 master checks.
- `npm run test:ui`: 62 interactive checks, including first-admin setup from the login page, navigation, filters, project/task/finance edits, administration and management drill-down.
- `npm run test:auth-ui`: 16 authentication checks across all six roles, rejected login, account isolation, mobile-table labels, late state responses and expired sessions.
- Review and production React builds are compiled separately.
- Responsive CSS provides stacked forms, card tables, retained search, wrapping grids, a closable navigation drawer, keyboard focus handling and bounded timeline scrolling. Real browser layout screenshots at device widths could not be tested: the supported browser skill is unavailable in this environment. JSDOM does not perform layout.
- SQL schema and migrations are unchanged by this release. SQL Server runtime validation still requires your staging server.


## Baseline release — 2026-10-12

43 Node domain tests (including six baseline scenarios), 10 baseline UI/API checks, 62 existing interactive checks, 16 authentication UI checks, and 24 Python API/relational/migration tests. The new tests cover immutable versions, schedule-reason validation, 10-day milestone slippage, original/current timeline bars, breakdown markers, management views, baseline selection, concurrent capture rejection, access filtering, and a preserving/idempotent v7-to-v8 migration on FK-enabled SQLite. SQL Server DDL is compiled for all 23 tables; it has not been executed on a real SQL Server. Review and production builds compile. The supported browser preview is unavailable; JSDOM interaction checks do not verify pixel layout.
