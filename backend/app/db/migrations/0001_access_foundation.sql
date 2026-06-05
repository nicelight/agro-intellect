-- TASK-001 local Account, FarmMembership, and session foundation.
-- @docs .memory-bank/tech-specs/FT-001-local-accounts-sessions-and-actor-context.md

CREATE TABLE accounts (
    account_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    login_identifier TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL CHECK (status IN ('active', 'invited', 'disabled')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by_account_id TEXT NULL REFERENCES accounts(account_id),
    updated_by_account_id TEXT NULL REFERENCES accounts(account_id)
);

CREATE TABLE farms (
    farm_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status = 'active'),
    one_farm_guard BOOLEAN NOT NULL DEFAULT TRUE UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (one_farm_guard IS TRUE)
);

CREATE TABLE farm_memberships (
    membership_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts(account_id),
    farm_id TEXT NOT NULL REFERENCES farms(farm_id),
    role_preset TEXT NOT NULL CHECK (role_preset IN ('boss', 'engineer', 'consultant')),
    status TEXT NOT NULL CHECK (status IN ('active', 'invited', 'disabled', 'removed')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    changed_by_account_id TEXT NULL REFERENCES accounts(account_id),
    UNIQUE (account_id),
    UNIQUE (account_id, farm_id)
);

CREATE TABLE local_sessions (
    session_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts(account_id),
    farm_id TEXT NOT NULL REFERENCES farms(farm_id),
    membership_id TEXT NOT NULL REFERENCES farm_memberships(membership_id),
    session_hash CHAR(64) NOT NULL UNIQUE,
    session_ref TEXT NOT NULL UNIQUE,
    auth_provenance_ref TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('active', 'revoked')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ NULL,
    last_seen_at TIMESTAMPTZ NULL,
    created_request_ref TEXT NULL,
    revoked_request_ref TEXT NULL,
    CHECK (session_hash ~ '^[a-f0-9]{64}$'),
    CHECK (session_ref LIKE 'sess_ref_%'),
    CHECK (auth_provenance_ref LIKE 'auth_ref_%')
);

CREATE INDEX idx_farm_memberships_account_status
    ON farm_memberships(account_id, status);

CREATE INDEX idx_local_sessions_account_status
    ON local_sessions(account_id, status);

CREATE INDEX idx_local_sessions_expires_at
    ON local_sessions(expires_at);

COMMENT ON TABLE local_sessions IS
    'Stores only backend-owned session hashes and redacted refs; raw session/auth material is forbidden.';
