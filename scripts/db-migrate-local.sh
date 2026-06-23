#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DRY_RUN=0

usage() {
  cat <<'USAGE'
Usage: bash scripts/db-migrate-local.sh [--dry-run]

Runs the local Alembic migration path against DATABASE_URL and reports sanitized
migration status.
USAGE
}

for arg in "$@"; do
  case "$arg" in
    --dry-run)
      DRY_RUN=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf '[db-migrate] ERROR: unsupported argument: %s\n' "$arg" >&2
      usage >&2
      exit 2
      ;;
  esac
done

log() {
  printf '[db-migrate] %s\n' "$*"
}

fail() {
  printf '[db-migrate] ERROR: %s\n' "$*" >&2
  exit 1
}

load_dotenv() {
  local env_file="$PROJECT_ROOT/.env"
  [[ -f "$env_file" ]] || return 0
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ -z "$line" || "$line" == \#* ]] && continue
    [[ "$line" == *=* ]] || continue
    local key="${line%%=*}"
    local value="${line#*=}"
    [[ "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || continue
    export "$key=$value"
  done < "$env_file"
}

cd "$PROJECT_ROOT"
load_dotenv

if [[ -x ".venv/bin/python" ]]; then
  PYTHON_BIN=".venv/bin/python"
else
  command -v python3 >/dev/null 2>&1 || fail "python3 is required. Run scripts/bootstrap-local.sh first."
  PYTHON_BIN="python3"
fi

if [[ "$DRY_RUN" == "1" ]]; then
  log "Dry run: would run Alembic ensure-version and upgrade head."
  log "Dry run: would inspect current migration revision without printing DATABASE_URL."
  log "Local migration command completed."
  exit 0
fi

"$PYTHON_BIN" - <<'PY'
from __future__ import annotations

import sys

from alembic import command
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory

from backend.app.config import AppSettings
from backend.app.database import build_database, redacted_database_url
from backend.migrations import build_alembic_config

settings = AppSettings.from_env()
database = build_database(settings)

try:
    print(f"[db-migrate] Target database: {redacted_database_url(settings.database_url)}")
    database.ping()
    config = build_alembic_config(settings)
    command.ensure_version(config)
    command.upgrade(config, "head")
    script = ScriptDirectory.from_config(config)
    heads = script.get_heads()
    with database.engine().connect() as connection:
        migration_context = MigrationContext.configure(connection)
        current_revision = migration_context.get_current_revision() or "base"
    head_status = ",".join(heads) if heads else "base"
    print("[db-migrate] Database connectivity: ok")
    print(f"[db-migrate] Alembic current revision: {current_revision}")
    print(f"[db-migrate] Alembic head revisions: {head_status}")
    print("[db-migrate] Local migration command completed.")
except Exception as exc:
    print(
        "[db-migrate] ERROR: migration failed "
        f"({type(exc).__name__}). Check local PostgreSQL service and .env credentials.",
        file=sys.stderr,
    )
    raise SystemExit(1)
finally:
    database.dispose()
PY
