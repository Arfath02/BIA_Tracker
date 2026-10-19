# Security review — BIA schema v7

Reviewed and updated 2026-10-01. This is an implemented application baseline with automated evidence, **not a certification or a claim that every security risk has been eliminated**. No BIA server, SQL database or external business system was accessed or changed.

## Implemented controls

| Control | Implementation and boundary |
|---|---|
| Server-side authorization | `production/access.py` filters every workspace response; `production/domain.py` authorizes every action against role, department, creator, assignment and explicit project grant. Management has full portfolio reads and no business writes. No browser-only permission checks. |
| Deny by default | Fixed command/role allowlists; unsupported actions fail. Unknown accounts and disabled accounts cannot create sessions. Only an existing admin can assign Management membership. HTTP bootstrap is disabled in the server edition. |
| Normalized integrity | 20 tables with PKs, FK links, uniqueness, amount/progress/date checks and same-project parent links. Database schema installation is an explicit operator action. No runtime DDL. |
| SQL injection | SQLAlchemy bound parameters for application data. Dynamic migration/permissions identifiers come only from fixed metadata/allowlists and identifier quoting. No request value is interpolated into SQL text. |
| Passwords | Argon2id (64 MiB, three iterations, parallelism two), random salts handled by the library, 12–128 character passwords. Hashes live in `user_credentials`, never in profile/state responses. Dummy hash verification reduces unknown-account timing disclosure. Passwords are not encrypted for later recovery. |
| Sessions | Random 48-byte tokens; only SHA-256 token digests stored in SQL. HttpOnly, Secure, SameSite=Strict cookies in production, eight-hour expiry, no localStorage authentication token. Reset/disable/role or department changes revoke affected sessions. |
| Authentication race | SQL Server transaction locks serialize state/security writes. Login rechecks the active account and password hash after expensive password verification before minting a session. |
| Brute-force resistance | SQL-backed per-account login/current-password throttling; Nginx per-source request limits on login and password endpoints. Password changes invalidate prior sessions. |
| CSRF and request validation | Exact trusted HTTPS origins, a required custom request header, JSON-only writes, bounded streamed body reads (20 KB), strict action/account schemas, range/length/date/business validation. Missing or foreign origins are rejected on the prototype as well. |
| Lost updates and partial writes | Workspace compare-and-swap version prevents stale edits. SQL mutations, history and dependent records commit/rollback together. Short workspace locks give coherent reads and authorization under SQL Server READ COMMITTED. |
| Audit/history | New progress updates link author IDs. Audit links actor and project IDs when known, retaining historical display snapshots. Runtime SQL role is denied UPDATE/DELETE on audit, progress history and settlements. This is append-only for the app, not tamper-proof against a DBA. |
| Least privilege | Separate DDL and runtime identities; object-level grants; no runtime schema modification. Old dbo tables are denied to the app after migration. `03_verify_runtime.sql` checks actual effective permissions and trusted constraints. |
| Transport | Browser HTTPS; SQL ODBC Driver 18 with encryption and certificate validation enforced in the connection factory. Raw ODBC override strings and insecure TLS flags fail closed. |
| Secret handling | SQL credentials only in server configuration; wizard writes mode 0600; no source/default credentials; no credential in the React bundle. Migration credentials are passed through process environment rather than shell arguments. Docker administrators can inspect container environment, so host admin access remains privileged. |
| Output/browser controls | React escapes normal text; no untrusted HTML rendering. CSV export escapes formula-leading values. Nginx enforces CSP, HSTS, nosniff, frame-ancestors none and restricted capabilities. API responses use no-store. |
| Error handling | Validation/integrity failures return generic messages; unexpected errors expose a reference ID, not SQL, parameters, stack traces or connection details. SQLAlchemy hides bound parameters in exceptions. |
| Deployment isolation | Non-root API/web images, read-only filesystems, dropped capabilities, no-new-privileges, private API network and local-only default HTTPS bind. SQL Server port is never published by the app. |
| Dependencies | Direct requirements plus a resolved Python 3.12/Linux lockfile; API image installs the lockfile. Full npm audit (including development tools) and Python requirement audit found no known advisories in their queried feeds on 2026-10-01. Vite/esbuild and the affected test-tool HTTP/WebSocket dependencies were updated; regression suites passed with the overrides. This is a point-in-time result, not proof of safety. |

## Deliberate boundaries

- Authentication is local to this application. Enterprise SSO, MFA, breached-password screening, self-service password recovery and forced initial-password rotation are not implemented. Use your approved private network/VPN and assess identity requirements before operational access; add SSO/MFA if required by BIA policy.
- The shared SQL service account is trusted application infrastructure. Project-level authorization is enforced by the API, not SQL Server row-level security. Users must not receive this SQL credential. A separate direct reporting/Access connection needs a deliberately restricted reporting design.
- All application writers currently use a short global workspace lock. This is simple and consistent for the expected internal portfolio, but throughput and large-portfolio pagination/load must be measured. Locks and totals have not been exercised on a real SQL Server here.
- Financial entries are tracking records, not payment execution or an accounting ledger. Project currency with explicit USD reporting conversion; full invoice settlement only. See COMMERCIAL.md for v10 scope. There is no procurement approval/signature workflow.
- No file uploads, remote URL fetch feature or arbitrary SQL execution feature is exposed. This limits several attack surfaces; it is not a universal SSRF/upload assessment.
- Logins and business changes are recorded, but this is not a complete SIEM security event pipeline. Authentication failure alerting, central tamper-resistant log forwarding and retention remain deployment work. Restrict logs and never log request bodies, passwords, cookies or connection strings.
- The private Sites prototype has an outer Sites access gate and a separate Worker/D1 implementation. It still uses the prototype PBKDF2 parameters and snapshot storage; the SQL Server edition uses Argon2id and normalized storage. Do not present the prototype as a verified production SQL deployment.

## Deployment acceptance still required

Your DBA/IT team must validate the real SQL Server version, encrypted connection and certificate chain; run installation/migration on a restored test database; verify runtime permissions and FK/CHECK trust; test multi-user concurrency, backups/restores, firewall/VPN and HTTPS; scan built containers and the Ubuntu host; establish patching and incident response; and conduct a risk-appropriate security test before operational use. Do not grant broad database roles to work around a denied operation. Actual SQL Server, Docker startup, browser pixel rendering and penetration testing were not available in this execution environment.

## Sources used to review the design

- OWASP Database Security: https://cheatsheetseries.owasp.org/cheatsheets/Database_Security_Cheat_Sheet.html
- OWASP Authorization: https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html
- OWASP Password Storage: https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html
- Microsoft primary/foreign key constraints: https://learn.microsoft.com/en-us/sql/relational-databases/tables/primary-and-foreign-key-constraints
- Microsoft ODBC authentication/encryption options: https://learn.microsoft.com/en-us/sql/connect/odbc/using-azure-active-directory

These are design references, not third-party approval of this implementation.


### Login boundary update — 2026-10-11

The React application does not mount the workspace or preload illustrative portfolio data before authentication. The review Worker now returns only authentication/setup flags for anonymous state requests; Python continues to return an empty anonymous state. Sign-out and session expiry unmount all workspace UI. State responses started before sign-out cannot restore the previous account's workspace. Identity, role or department changes remount the workspace to clear local filters, dialogs and management drill-down selection. Server-side project visibility and mutation permission checks remain authoritative. The UI hides planning and financial mutation actions from roles that cannot use them.

Automated JSDOM checks exercise all six roles, rejected login, scoped dashboards, sign-out/account switching, a delayed pre-logout state response and expired sessions against an isolated real Worker API. These checks are not a penetration test or visual browser/device certification.
