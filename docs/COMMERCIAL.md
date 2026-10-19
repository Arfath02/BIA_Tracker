# Updated in v11

Read [EXPENSES.md](EXPENSES.md) for the current travel forms, JOD costs, expense roll-ups and migration. The v10 travel/cost treatment described below is historical.

# Currency, payment conditions and consultant travel — v10

## Where to use the new features

- Create a subproject: select a currency and external vendor. The amount input shows the chosen currency after leaving the field. USD needs no conversion rate. Other currencies require a positive **USD per 1 unit** rate and its date.
- Open a project → **Finance**: view original-currency budgets, POs, invoices and settlement details; use **Currency, budget & vendor** to maintain project settings; add payment conditions triggered by a date or a project milestone. Finance and administrators manage conditions and settlements. Planners maintain commercial settings.
- For each condition, create a PO and use **Link new invoice**. The linked invoice must equal the condition amount; one invoice per condition. Record payment after the invoice is fully settled, including payment reference and date. Installments can be represented as separate conditions/invoices. No bank transfer is initiated.
- Due date (including today), overdue and completed-milestone conditions show persistent workspace reminders, scoped by project access. An unpaid invoice also appears when its invoice due date arrives, even when its linked milestone remains incomplete. Paid invoices clear the corresponding reminders. Reminders refresh with workspace data (45 seconds / focus / successful saves). They are in-app notices, not email, Teams, push or background scheduled messages.
- Project → **Travel**: add vendor consultants and individual visits. Each visit records arrival/departure, BIA flight/accommodation/food responsibilities, campus or external stay, and booking date/cost when a BIA flight is booked. Repeat visits are separate records.
- Admin portal → **Master data → Vendors**: create, rename or deactivate vendors. Existing references use stable IDs. **Vendor consultants** at the top of Admin portal maintains consultant master records. Administrators manage all consultants; department heads add and edit project-managed consultants in their authorized department projects. A displayed project lead name is not an authentication grant. Shared admin-managed consultants can be used on matching-vendor projects, but only administrators can rename them.

## Reporting and accounting boundaries

Dashboard figures always use **USD millions with exactly three decimals**, for example `USD 0.480 M`. Detail lists and forms use original project currency and ISO minor-unit precision. Dates include the year. CSVs include source currency, amount, reporting rate and USD amount.

The catalog is the SIX ISO 4217 List One published 17 September 2026, retrieved 13 October 2026: 165 currency/fund codes with numeric minor units. Non-currency/test/precious-metal entries with undefined minor units are not offered. Source: https://www.six-group.com/dam/download/financial-information/data-center/iso-currrency/lists/list-one.xml . The versioned catalog is in `shared/currencies.json`; it is validated on both backends and represented by a read-only SQL lookup table. New ISO amendments require a controlled catalog/schema-data update.

USD totals use a manually entered project reporting rate. **These are reporting translations, not live FX quotes, booked accounting exchange gains/losses or historical-rate valuations.** Changing the rate is audited and recalculates current USD totals. Currency cannot change after POs, payment conditions or trips exist. Existing data remains USD at rate 1. Purchase orders and invoices inherit project currency. Budget and PO limits compare original-currency amounts.

Travel booking costs are informational records in project currency and do not automatically add to commitment/invoice totals. Record a related PO/invoice separately where applicable, avoiding double counting. Flight rates are not supplied automatically. Accommodation and food responsibilities are captured; their costs are not additional invoice records.

## Storage and deployment

Schema v10 has **30 normalized tables**. New tables: `currency_codes`, `project_finance`, `payment_terms`, `invoice_terms`, `vendor_consultants`, `consultant_trips`. Monetary storage is `DECIMAL(19,4)` with currency-specific precision validation; exchange rates are `DECIMAL(18,8)`. IDs, foreign keys, unique invoice-condition links, date/amount checks and immutable payment records protect relational integrity. Existing amount columns are widened without changing amounts.

Back up the database and stop the API. Build the updated containers. Use `python3 deploy/migrate.py` with the separate migration identity, or on **v9 only** run `deploy/sql/06_upgrade_v9_to_v10.sql` in SSMS. Reapply `02_runtime_permissions.sql`, then start the updated application. New databases use `01_schema.sql`. The API container includes the shared currency catalog. No external BIA SQL system was modified during development.

The Sites edition retains its private review snapshot storage; the self-hosted edition uses the normalized Python/SQL Server adapter. Both enforce the same actions, currency precision, project visibility and roles. Updates use the existing transaction/version boundary; failed or stale writes do not partially persist.

## Validation scope

Automated JavaScript domain tests, Python API/relational tests and DOM-driven UI tests cover the new flows, access filtering, duplicate/invalid links, precision, settlement history, repeat travel, stale writes and preserving migration. SQL Server DDL is generated/compiled; tests run on an isolated SQLite adapter, not a live SQL Server. Actual SQL Server upgrade/restore rehearsal remains required. Browser rendering on target devices and visual responsive acceptance remain required; DOM flow tests do not establish physical-device layout quality.
