#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DRY_RUN=0

usage() {
  cat <<'USAGE'
Usage: bash scripts/bootstrap-farm-local.sh [--dry-run]

Creates or reuses the canonical local Farm and tomato_001 after FT-002 migration.
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
      printf '[farm-bootstrap] ERROR: unsupported argument was rejected safely.\n' >&2
      usage >&2
      exit 2
      ;;
  esac
done

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
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
else
  printf '[farm-bootstrap] ERROR: Python is required. Run scripts/bootstrap-local.sh first.\n' >&2
  exit 1
fi

if [[ "$DRY_RUN" == "1" ]]; then
  printf '[farm-bootstrap] Dry run: would create or reuse canonical Farm and tomato_001.\n'
  exit 0
fi

"$PYTHON_BIN" - <<'PY'
from __future__ import annotations

import sys

from backend.app.access_admin import CanonicalFarmBootstrapError, bootstrap_canonical_farm
from backend.app.config import AppSettings
from backend.app.database import build_database

database = build_database(AppSettings.from_env())
try:
    with database.session() as session:
        result = bootstrap_canonical_farm(session)
    changes = int(result.farm_created) + int(result.plant_created)
    print(f"[farm-bootstrap] Canonical Farm bootstrap completed; records created: {changes}.")
except CanonicalFarmBootstrapError as exc:
    print(f"[farm-bootstrap] ERROR: {exc}", file=sys.stderr)
    raise SystemExit(1)
finally:
    database.dispose()
PY
