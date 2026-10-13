# Automatic scheduling and weekly calendars — schema v9

Open any subproject and select **Edit working week**. Check its weekly days off (Sunday through Saturday), enter a reason, and save. At least one day must remain working. New subprojects include the same controls. Existing projects retain a seven-day working week until an owner configures their calendar; installation never rewrites live dates.

Changing a task's dates reschedules its unstarted finish-to-start successors and their successors. A successor starts on the next working day after the latest predecessor finishes, using the successor's subproject calendar. Its previous inclusive working-day duration is preserved. Manual gaps in the affected chain are replaced by this earliest feasible schedule; unrelated tasks are untouched. Selected non-working start/finish dates roll forward. Multiple predecessors are respected. Summary dates expand to contain children and their successors are included. Project boundaries extend where required; approved baselines are immutable and delay indicators/graphs continue comparing against them. Project boundaries are not automatically shortened.

When recording 100% before the current planned finish, a confirmation offers **Complete and reschedule**, **Complete, keep dates**, or **Back**. Completion is recorded as today's date in the application's Asia/Amman reporting timezone. Confirming advances unstarted successors (including subsequent levels); declining retains their dates. This is not a backdated actual-completion entry form. Started/completed successors are not moved automatically. A delay conflicting with started work is rejected atomically for a planner to resolve. The task's planned finish is retained for baseline/history reporting; completion timestamp drives subsequent dependencies.

Weekly calendar changes reflow unstarted tasks and affected successor chains; working durations are measured under the old calendar. Started work remains unchanged. Public holidays, date-specific exceptions, lag/lead offsets, resource levelling and critical-path calculation are not included.

Administrators and the responsible department head can edit calendars/plans. A head cannot silently move another department's schedule: the whole command fails and asks for an administrator. Assigned delegates may confirm an early-completion cascade within the same subproject; cross-project cascades require a planner with permission for the affected projects. Management remains read-only. Each changed task receives an append-only audit entry with old/new dates; writes use the existing atomic workspace version check.

## SQL Server upgrade

Back up the dedicated database and stop the tracker API. Build the new image/source. Use `python3 deploy/migrate.py` with the migration identity (preserving v7/v8 → v9), or for an existing **v8** database run `deploy/sql/05_upgrade_v8_to_v9.sql` in SSMS. Reapply `deploy/sql/02_runtime_permissions.sql`, then start the updated API and frontend. The application needs schema v9. Fresh installations use `01_schema.sql`.

`bia.project_days_off` has a composite primary key `(projectId, weekday)`, a project foreign key, and weekday check 0–6 (Sunday=0). No stored JSON or credentials are introduced. An empty set means every day is working. The API additionally prohibits all seven days being off. Runtime rights are SELECT/INSERT/DELETE for this table, without DDL access.

## Verification

Node domain tests cover multi-level cascading, mixed calendars, multiple predecessors, immutable baselines, started work, department authorization, summary rollups and both early-completion choices. JSDOM + local Worker API exercises the calendar form and early-completion popup. Python tests check equivalent API behavior, normalized persistence and preserving migration. SQL Server DDL is compiled, but an actual SQL Server instance and visual device/browser QA are not available in this environment.

## Confirmation, baseline reminders and early-delivery reporting

Editing an existing task's start or finish and selecting Save opens **Confirm task date change**. The popup shows previous/requested dates and explains the automatic successor cascade. Nothing is written before confirmation. **Cancel — restore old dates**, the close button, or Escape restores the editor's old date values. Confirmation submits against the workspace version captured when editing began; stale changes remain rejected by the API.

The workspace shows a notification listing projects without a baseline. Authorized planners can open Save baseline directly; other viewers are directed to the project owner. Projects without tasks first need a task plan. Each unbaselined project also displays a reminder in its detail panel and date-change confirmation.

Once all leaf tasks are 100%, projects with recorded completion dates show **Completed X days early** when the last leaf completion is before the original baseline target (or the current project target when no baseline exists, clearly labelled). The metric uses calendar days and the reporting timezone. Missing completion history is never inferred from a planned date; reopened or incomplete projects do not qualify. The overview, project detail, management project list, department totals and management KPI show early delivery. A later revised planned date cannot erase or inflate the original-baseline comparison. No SQL schema changes are required beyond v9.
