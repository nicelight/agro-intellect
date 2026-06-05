-- TASK-013 local_only SyncStatus contract.
-- @docs .memory-bank/tech-specs/FT-017-local-privacy-deployment-controls-and-secret-redaction.md
--
-- ⚠️  server_verified, upload status, cloud availability, server copy,
--     and remote backup fields are forbidden in MVP.  The CHECK constraint
--     ensures sync_status can NEVER be set to a non-local_only value
--     until a future migration explicitly relaxes it.

ALTER TABLE farms
    ADD COLUMN sync_status TEXT NOT NULL DEFAULT 'local_only'
    CHECK (sync_status = 'local_only');

COMMENT ON COLUMN farms.sync_status IS
    'MVP sync status: local_only only. server_verified and other sync values are forbidden until a later server-sync PRD/spec exists.';
