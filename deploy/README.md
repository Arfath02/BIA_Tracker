# BIA Project Portfolio — Ubuntu + React + Python + Microsoft SQL Server

## Architecture

Browser → internal HTTPS Nginx (8443) → FastAPI (8000, Docker network only) → existing SQL Server over encrypted ODBC 18. React assets and `/api` share one origin. SQL Server is not bundled, published or reconfigured by this package. Use a dedicated database, migration login and least-privilege runtime login.

Tables are normalized: master projects, departments, vendors, resources, roles, workspace version, schema migration records, users, user credentials, sessions, login attempts, projects, project department-access grants, tasks, task predecessors, purchase orders, invoices, invoice settlements, progress updates and audit log. POs and invoices use decimal monetary columns, foreign keys and uniqueness constraints. Mutations validate business rules, claim the expected workspace version and write related records in one database transaction. The version update serializes competing writes and produces HTTP 409 on stale edits.

Session tokens are random and stored only as SHA-256 hashes. Browser cookies are Secure, HttpOnly, SameSite=Strict and expire after 8 hours. Password resets, password changes and changes to another account’s role, department, email or active status revoke sessions. The backend uses Argon2id for passwords, rate limits per email, and Nginx adds per-IP login limits. Every state read grants the administrator and explicit Management role full portfolio visibility; other roles are filtered using creator, head, task-assignee or department-group access. Management is denied at the start of every business mutation and cannot administer accounts or sharing. Its own password/session operations remain available. Every business mutation checks project visibility before role/department rules. Removing grants applies on the next request, including direct requests with previously known IDs. Cross-project predecessor IDs outside a user’s scope are redacted; their constraints remain enforced when editing or updating tasks. Parameterized SQLAlchemy statements are used throughout. Request sizes, content types and trusted origins are checked. No browser storage contains passwords or session tokens.

## Guided operator setup

Follow [START_HERE.md](../START_HERE.md). `configure.py` creates a permission-0600 `.env` without connecting to SQL Server. `setup.sh` builds the containers, checks the runtime connection, prompts for separate migration credentials, installs/upgrades the schema, pauses for DBA permission grants, creates the initial administrator and starts the application. None of these commands were executed against BIA systems during development.

Always use `docker compose --env-file deploy/.env -f deploy/compose.yaml` from the repository root. The API service's `env_file` supplies database configuration to the container; Compose's `--env-file` separately supplies interpolation for the host IP, HTTPS port and TLS directory.

`production.manage upgrade` is idempotent for schema v7 and copies recognized v1–v6 dbo data into 20 normalized bia tables transactionally. It preserves source tables and financial totals, verifies entity IDs, and does not copy active sessions. See [DATABASE_SETUP.md](../docs/database/DATABASE_SETUP.md) for exact migration, permissions, validation and rollback instructions. Never run the fresh-install SQL against an existing installation.

The default runtime connection uses encrypted ODBC 18 with certificate validation. For a private SQL CA, put public CA certificates in `deploy/ca-certificates/*.crt` before building the API image. Keep private keys out of that directory. The application HTTPS certificate is mounted separately into Nginx; permit UID 101 to read its private key using an owner/group/ACL policy without making it world-readable.

Production starts with editable default departments and an Unassigned resource, without sample projects or financials. The HTTP setup endpoint is disabled; the operator creates the first admin with `python -m production.manage create-admin`.

## Runtime database privileges

Use `deploy/sql/02_runtime_permissions.sql` as the exact object-level grant list. It denies changes to role/schema definitions and existing audit, progress and settlement records. It also denies access to retained legacy dbo tables after migration. Then run `03_verify_runtime.sql` as the runtime identity. Do not grant broad database roles or schema-alter permissions to the runtime login; the installer uses separate DDL privileges.

## Before production acceptance

- Execute the integration suite against a disposable SQL Server instance with ODBC 18, trusted SQL TLS and the final privilege set. Local tests used SQLite and SQL Server DDL compilation only.
- Verify management account creation/removal, every read-only boundary, department→project→task drill-down, browser sign-in, task/subtask creation, delegated progress, dependency conflicts, concurrent changes, PO/invoice balances, account revocation and keyboard/mobile layouts on the actual private hostname.
- Decide whether to replace local application passwords with Microsoft Entra ID/OIDC and MFA. The current package does not claim an Entra integration.
- Configure database backups, encrypted off-host copies, tested restores, monitoring and an incident owner. Set a retention policy for audit/progress records and exports.
- Review images/dependencies, pin deployment image digests after scanning, scan for secrets, perform security review and load-test the expected user/task volume.
- Start with approved LAN/VPN access. No public deployment or external integration is configured here.

The API reads a workspace snapshot internally and returns only authorized project records to each account. Shared dropdown catalogs are workspace-wide. At larger operational scale, replace snapshot reads with paginated database queries that preserve the same access rules. SQL Server row-level security is not configured; project authorization currently resides in the Python API. The runtime database credentials must never be available to end users.
