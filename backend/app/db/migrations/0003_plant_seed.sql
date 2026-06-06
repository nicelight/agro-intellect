-- TASK-006 single Farm workspace and tomato_001 Plant seed.
-- @docs .memory-bank/tech-specs/FT-002-farm-plant-lifecycle-and-plant-access-grant.md

CREATE TABLE IF NOT EXISTS plants (
    plant_id TEXT PRIMARY KEY,
    farm_id TEXT NOT NULL REFERENCES farms(farm_id),
    canonical_label TEXT NOT NULL,
    display_name TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'active' CHECK (state IN ('active', 'archived')),
    created_by_actor_ref TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    archived_at TIMESTAMPTZ NULL,
    archived_by_actor_ref TEXT NULL,
    archive_reason TEXT NULL,
    restored_at TIMESTAMPTZ NULL,
    restored_by_actor_ref TEXT NULL
);

CREATE TABLE IF NOT EXISTS plant_access_grants (
    grant_id TEXT PRIMARY KEY,
    farm_id TEXT NOT NULL REFERENCES farms(farm_id),
    plant_id TEXT NOT NULL REFERENCES plants(plant_id),
    account_id TEXT NOT NULL REFERENCES accounts(account_id),
    membership_id TEXT NOT NULL REFERENCES farm_memberships(membership_id),
    state TEXT NOT NULL DEFAULT 'granted' CHECK (state IN ('granted', 'revoked')),
    can_view BOOLEAN NOT NULL DEFAULT TRUE,
    can_work BOOLEAN NOT NULL DEFAULT TRUE,
    plant_approve_actions BOOLEAN NOT NULL DEFAULT FALSE,
    created_by_actor_ref TEXT NOT NULL DEFAULT '',
    updated_by_actor_ref TEXT NOT NULL DEFAULT '',
    revoked_at TIMESTAMPTZ NULL
);

CREATE INDEX IF NOT EXISTS idx_plants_farm_state
    ON plants(farm_id, state);

CREATE INDEX IF NOT EXISTS idx_plant_access_grants_plant
    ON plant_access_grants(plant_id);

CREATE INDEX IF NOT EXISTS idx_plant_access_grants_account
    ON plant_access_grants(account_id);

-- Seed tomato_001 as the initial Plant.
-- The farm_local Farm must already exist via earlier migration/seed.
INSERT INTO plants (plant_id, farm_id, canonical_label, display_name, state, created_by_actor_ref)
SELECT 'tomato_001', 'farm_local', 'Tomato 001', 'Tomato 001', 'active', 'system_seed'
WHERE NOT EXISTS (SELECT 1 FROM plants WHERE plant_id = 'tomato_001');
