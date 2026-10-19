# Budget change requests and portfolio Gantt — schema v12

## Budget workflow

1. Open the subproject → **Finance → Request budget change**. Enter a title, positive additional amount in the project currency, and business justification.
2. The request is **Pending**. It has no effect on the approved budget, PO capacity or existing invoices.
3. A **different** administrator or finance user opens **Financial control → Approvals → Review request**. They approve or reject it with a reason. The central queue provides only the request and minimal budget summary for otherwise inaccessible projects; normal project access still applies to tasks, POs and invoices.
4. Approval atomically records the reviewer, decision date and before/after budget and adds the amount once. Rejection leaves the budget unchanged. Submitted content and terminal decisions are immutable; reject an incorrect request and submit a replacement.
5. Finance/Admin may **Create additional PO** within the revised budget. Use **Add change invoice**, choose the correct PO, enter invoice number/dates and verify the amount. The invoice is linked to the approved request and the PO. Multiple invoices are permitted up to the request's total amount; every invoice is also checked against the remaining PO amount.
6. Record payment with the existing settlement workflow. Neither invoicing nor payment adds the change amount to the budget again.

A project has these distinct figures:

- Original budget: the approved amount before this release's first approved change.
- Approved changes: the sum of approved positive change amounts.
- Revised approved budget: original budget + approved changes. This is the budget used by project, master, department and portfolio totals and PO validation.
- Pending changes: visible separately, excluded from approved totals.
- Invoiced/paid: existing accounting records, not additional budget approvals.
- Other expenses: the existing JOD travel/spares/miscellaneous calculation, kept separate. Budget + other expenses uses the revised approved budget.

An invoice alone is not evidence of approval. This workflow therefore approves the extra budget before accepting the additional linked invoice. There is no file attachment upload in this release: invoice details are entered as records. Budget decreases, credit notes, cancellation of approved requests and approval chains are not implemented. Ordinary budget edits are now blocked server-side; changing project currency/vendor remains a separate form, and currency is locked once a request exists. Historical budgets are preserved as the opening amount; previous changes cannot be reconstructed from unavailable history.

To test separation of duties, create a second application Admin or Finance account through **Admin portal → Users**. Finance users can review in the central approval inbox. Give them project access through **Manage access** only if they also need POs, invoices or other project details. The Sites owner-private gate is unchanged; these are application accounts, not public access grants.

## Gantt navigation

- **Overview, All master projects:** the Project Gantt initially shows master-project date spans. Click a master name to see its subprojects, then a subproject to see its tasks/subtasks.
- **Overview, selected master:** the chart starts with all of that master's subprojects.
- **Detail level → All tasks and subtasks:** shows task-level schedules for every project in the current scope, grouped under project rows.
- **Project → Timeline:** opens that project's task Gantt directly.
- **Project execution → Timeline:** shows a Gantt for the existing department/project/task filters.
- **Management dashboard:** has the same chart; it follows the selected master, department and project drill-down. Management remains read-only.
- Use the chart's master/subproject dropdowns and breadcrumb to navigate. Fit, Months and Weeks provide different display scales. Charts scroll horizontally and vertically; names and the date axis stay visible.

Bars show current dates and progress; baseline bars show saved dates, delayed/overdue work is marked red, milestones show diamonds, and a dashed line marks today when within the displayed range. Task labels show predecessor names (hidden projects' details are not exposed). All displayed dates include the year. There is no drag-to-reschedule action: date changes still use the validated scheduling/confirmation workflow. Budget approval does not alter task dates or schedule baselines.

Master date spans use the earliest subproject start and latest finish. A master baseline is drawn only if every included subproject has a baseline. Progress remains weighted by planned leaf-task hours. One-day tasks occupy one full day. Only projects returned by the role-scoped API appear.

## Deployment and data model

Schema v12 adds `budget_change_requests` and `invoice_budget_changes` to the existing normalized model (35 tables total). The request stores immutable submitted details and a controlled decision, with FK references to project/requester/reviewer, decimal amounts and status/budget checks. Invoice links are one-to-many from an approved request and immutable once recorded. Application transactions enforce cross-project matching, approval status, capacity and optimistic concurrency; the runtime account has no DDL or invoice-link update/delete privileges.

Back up, stop the API, then run `deploy/sql/08_upgrade_v11_to_v12.sql` with a DBA/migration identity for an existing v11 database. For earlier versions use `python3 deploy/migrate.py`. Reapply `02_runtime_permissions.sql`, deploy the current frontend/API together, and run `03_verify_runtime.sql` as the runtime account. New empty databases use `01_schema.sql`. Updated editable ERD sources and an offline HTML view are in `docs/database`.

The private Sites prototype and the Python/SQL Server deployment are separate storage adapters. This release does not connect to or alter BIA's external SQL Server. Local automated validation uses the Worker/D1 emulator and SQLAlchemy/SQLite; live SQL Server, Ubuntu hosting and real-browser visual checks still require validation in the deployment environment.
