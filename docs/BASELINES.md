# Schedule baselines and delay tracking

## Save and use a baseline

1. Sign in as an administrator or the responsible department head.
2. Open the subproject from the portfolio. Under **Schedule baseline**, choose **Save baseline**.
3. Give it a name and record the approval/reason. The server snapshots the project dates and every task's ID, title, parent, start, finish, effort and milestone classification. No client-supplied snapshot dates are accepted.
4. Open a task plan. Mark important delivery gates with **Mark as a key milestone**. The diamond appears at the current target date. Milestones remain planned deliverables with their existing effort weighting; they are not a separate zero-effort scheduling engine.
5. Change task dates and enter a **Schedule change reason**. If the change extends beyond the project boundary, first use **Revise project dates** to extend that boundary. Parent containment and predecessor/successor validation still apply. Dates are not automatically cascaded to successors.
6. Open **Timeline** to compare the dashed original bars and current plan. Open **Breakdown** for task/subtask completion bars with delay labels. Management gets both charts in department → project drill-down.

## Baseline versions

A saved baseline cannot be edited or deleted in the app. **Save new baseline** adds another numbered snapshot; it never replaces the original. All views default to v1. **Comparison baseline** selects a different version for that project for the current browser session, including its management views. Signing out resets comparison choices. There is no silent re-baselining after a date edit. Create a baseline for each subproject you want to monitor; subproject delay flags roll up to master and department summaries. Existing records are not automatically labelled as an approved historical plan during migration.

## What the numbers mean

- Finish variance is current target minus saved target, in calendar days. Moving a target later flags a delay immediately, even if both dates are in the future.
- Incomplete work past its original baseline finish remains delayed even if the current target is extended.
- Recorded completion dates come from progress updates in Amman time. Completed tasks remain Complete; their schedule badge retains a late-completion or revised-finish indication. Where no completion event exists, the app cannot infer an actual completion date.
- The project delay figure is the **largest** project/task variance. It is an exception flag, not a critical-path forecast or a sum of all task delays. A delayed noncritical task can therefore flag a project whose final contractual date has not changed.
- Existing blocked, predecessor and overdue checks remain active. Project risk counts include delayed projects. Progress percentage still describes completion, never a manual schedule override.
- **Planned today** is an indicative linear plan between baseline start/finish dates, using frozen leaf-task effort. A marked milestone becomes planned complete at its target date. **Actual** uses the same saved task scope and weights, so task additions or effort edits cannot dilute the baseline denominator. The difference is percentage points, not days or earned value.
- Tasks added after capture say **Added after baseline**; projects without a saved baseline say **No baseline**. They are never presented as zero-variance approved work.
- A milestone flag identifies an important delivery task; it retains the app's normal date, dependency, effort and progress validation.

## Access, storage and installation

Only administrators or the responsible head with project visibility can capture baselines or revise dates. Delegates retain assigned-progress permission only. Management, executive and finance cannot save baselines. Baseline records are filtered by project access on both APIs. Writes use the existing workspace version check and transaction boundary; stale concurrent captures are rejected.

Python/SQL Server schema v8 adds `bia.task_milestones`, `bia.project_baselines` and `bia.baseline_tasks`. The last two are append-only for the runtime database role. The Site review backend retains these snapshots in its existing transactional review storage; your self-hosted build uses normalized relational tables.

For an existing normalized v7 SQL Server installation: stop the API, take and verify a backup, run `python3 deploy/migrate.py` with your migration identity **or** run `deploy/sql/04_upgrade_v7_to_v8.sql` in the dedicated application database. Do not use the fresh-install schema script to upgrade an existing database. Reapply `02_runtime_permissions.sql`, check `03_verify_runtime.sql` with the runtime identity, and then deploy the new API/frontend together. The Python migration is repeatable. The standalone SQL upgrade deliberately refuses an already upgraded database.

For a fresh database, use `01_schema.sql` (now v8), then permissions and the documented administrator creation command. No migration or query has been executed on your own SQL Server by this release.
