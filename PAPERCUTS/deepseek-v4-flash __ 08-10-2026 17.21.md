# Papercuts

## Parallel pytest runs share PostgreSQL catalog scans
Two concurrent `pytest` processes against the same `agro_intellect` DB
interfere: `tests/backend/dataset_governance/test_migration_models.py::test_ft014_migration_upgrade_downgrade_roundtrip`
and the conftest upgrade use schema-unqualified catalog queries
(`pg_type ... LIKE 'dataset_%'`, `pg_tables where tablename=...`), so process A's
mid-test enums/table leak into process B's assertions. Sequential runs pass
(11 passed) and each run creates/drops an isolated UUID schema; the isolation is
per-schema but the assertions are catalog-wide. Root cause is my own parallel
probe invocation; the fix is to run PG-dependent pytest gates sequentially.
Also: crashed probe runs left stale `task047_*` / `task041_*` schemas behind
(cleanup in conftest `finally` did not always run), which must be dropped before
re-running catalog-wide assertions.
