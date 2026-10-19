# Consultant travel and other expenses — schema v11

## Using the changes

- Open a project → Travel → Add consultant. Enter name and designation. If the project has no vendor, select a vendor and confirm assigning it to this project. Saving both changes is atomic. The consultant appears in the project directory and visit dropdown immediately. Shared consultants already created under Admin appear when their vendor is selected under Finance → Currency, budget & vendor. Existing consultants with no designation can be edited to add one.
- Add each consultant visit separately. Flight bookings use JOD, with a booking date. Accommodation is BIA campus or Hotel accommodation. For hotels, select BIA booked or Vendor booked. Only BIA-booked hotels have a BIA hotel cost. Record BIA visa costs in JOD. The food field has been removed from the UI; historical values remain preserved in storage.
- The Spares and Miscellaneous tabs accept expense date, PR number and JOD amount. Both support remarks. A PR number must be unique within a project and category. Edit an entry to correct it; the audit records the change.
- JOD amounts allow three decimal places. Bracketed USD values use the BIA reporting policy **JOD × 1.4** and are displayed to USD cents. This is a fixed configured policy, not a live exchange-rate feed. Calculations retain four USD decimal places before display.
- Other expenses = BIA booked flights + BIA booked hotel costs + BIA visa costs + spares + miscellaneous. Campus stays, vendor-arranged flights and vendor-booked hotel costs contribute zero. Every recorded visit is counted once. Project and portfolio figures show USD millions with three decimal places. Management's summary follows the selected master/department/project scope.
- Budget + other expenses means **approved project budget converted to USD + recorded additional expenses**. It is not an invoice-paid or actual-cash-spend figure. POs, invoices and paid totals retain their original meanings. Do not include the same additional costs in both the base approved budget and additional-expense records if you want a non-duplicated combined total.

## Existing travel data

Old flights retain their original project-currency amount. Until edited, their USD contribution uses the project's existing USD reporting rate. They are labelled “legacy currency” in Travel. Editing prefills a JOD equivalent (original amount × project USD rate ÷ 1.4, rounded to three JOD decimals); the form displays the original value for review. Saving explicitly adopts the JOD cost policy. New `trip_costs` rows identify this treatment; the application never silently reinterprets an old project-currency flight amount as JOD. Old external stays are displayed as hotels with no hotel cost recorded.

## SQL Server installation and migration

Schema v11 has **33 normalized tables**. It adds three tables, all with primary keys and foreign keys:

| Table | Purpose |
|---|---|
| `consultant_details` | Consultant designation, one-to-one with vendor consultant |
| `trip_costs` | JOD flight, hotel and visa amounts and hotel booking responsibility, one-to-one with visit |
| `project_expenses` | Project-linked spares and miscellaneous PR expense records |

JOD amounts use `DECIMAL(19,3)`. Checks enforce positive/nonnegative values, valid categories and booker values. Unique project/category/PR keys prevent duplicate entries. No existing table is dropped or rewritten by the v10-to-v11 upgrade. The previous trip `flightCost` column remains a compatibility mirror; when a `trip_costs` row exists, `flightCostJod` is authoritative for reporting.

Back up and stop the API before migration. For v10, run `deploy/sql/07_upgrade_v10_to_v11.sql` as the migration/DBA identity, or use `python3 deploy/migrate.py`. Earlier installations use the preserving Python migrator. Reapply `02_runtime_permissions.sql`, deploy the updated API/frontend together and run `03_verify_runtime.sql` as the runtime identity. Fresh databases use `01_schema.sql`. Do not run the fresh-install script over an existing database.

Admins and project department heads maintain travel. Admins, scoped finance users and project department heads maintain additional expenses. Management remains read-only. Project visibility is enforced server-side before mutations; costs are filtered with the visible project scope. SQL writes use SQLAlchemy bound parameters. React renders names/remarks as text. Normal session, CSRF/origin, optimistic version and audit controls remain in place.

The private Sites prototype stores review data separately from the Python/SQL Server edition. Publishing does not migrate data to an external SQL Server. Live SQL Server execution, Ubuntu deployment and browser visual verification were not available in this development environment.
