# Python API reference — 2026-10-18.1

All paths use the same HTTPS origin as React. Login issues a Secure, HttpOnly, SameSite=Strict session cookie; the browser must retain it. Write requests require `Content-Type: application/json`, `X-BIA-Request: 1`, and the exact allowed `Origin`. No API key or database password belongs in frontend code.

| Method | Route | Purpose |
| --- | --- | --- |
| GET | /api/health | Database/schema check and API release identifier |
| GET | /api/state | Authorized workspace snapshot and workspace version; unauthenticated response has no project data |
| POST | /api/login | Email/password login |
| POST | /api/logout | Revoke current session |
| POST | /api/mutate | Business command, payload and current workspace version |
| POST | /api/users | Create permitted user account |
| POST | /api/users/active | Enable/disable account with role checks |
| POST | /api/users/reset-password | Admin reset of another user's password, with workspace version |
| POST | /api/password | Change own password and revoke old sessions |
| POST | /api/setup | Deliberately disabled on self-hosted production; use operator create-admin |

`/api/mutate` JSON envelope: `{"action":"expense","version":42,"payload":{"projectId":"actual-project-id","kind":"spares","date":"2026-10-18","prNumber":"PR-001","amountJod":12.345,"remarks":"Spare part"}}`.

Read the current version from `/api/state` before saving. HTTP 409 means no write was accepted; refresh and review before resubmitting. The server validates payload fields and authorization; acceptance of an action name alone does not grant permission.

Supported actions: project, task, update, po, invoice, payment, catalog, user_edit, master, project_access, baseline, project_dates, project_calendar, project_commercial, payment_term, consultant, trip, expense, change_request, change_decision.

`docs/API_OPENAPI.json` is an offline contract generated from FastAPI. Its generic mutation payload is validated by the domain/commercial handlers; consult `tests/test_python_api.py` and `tests/test_commercial.py` for working examples. Interactive API documentation is disabled in production. Do not set BIA_TESTING=1 on a deployed server: that flag relaxes cookie HTTPS behavior only for isolated tests.
