SQL Server schema v12, 35 normalized tables.
Fresh database: deploy/sql/01_schema.sql
Existing database: use migration steps from the full-source RELEASE_GUIDE.md. Never run the fresh-install script over existing data.
Apply 02_runtime_permissions.sql and verify as runtime identity using 03_verify_runtime.sql.
ER diagrams and data dictionary: docs/database/.
Python code/shared definitions included for schema reference. Use the FULL SOURCE archive for runnable application deployment and migration tooling.
This release repairs Python API action validation; SQL remains v12.
