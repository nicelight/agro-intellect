#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DRY_RUN=0
LOGIN_NAME=""
DISPLAY_NAME=""

usage() {
  cat <<'USAGE'
Usage: bash scripts/bootstrap-first-boss-local.sh --login-name <login_name> --display-name <display_name> [--dry-run]

Creates the first active Boss after the canonical Farm bootstrap has completed.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --login-name)
      [[ $# -ge 2 ]] || {
        printf '[first-boss-bootstrap] ERROR: missing login name value.\n' >&2
        exit 2
      }
      LOGIN_NAME="$2"
      shift 2
      ;;
    --display-name)
      [[ $# -ge 2 ]] || {
        printf '[first-boss-bootstrap] ERROR: missing display name value.\n' >&2
        exit 2
      }
      DISPLAY_NAME="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf '[first-boss-bootstrap] ERROR: unsupported argument was rejected safely.\n' >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "$LOGIN_NAME" && "$DRY_RUN" == "0" ]]; then
  printf '[first-boss-bootstrap] ERROR: --login-name is required.\n' >&2
  exit 2
fi

if [[ -z "$DISPLAY_NAME" && "$DRY_RUN" == "0" ]]; then
  printf '[first-boss-bootstrap] ERROR: --display-name is required.\n' >&2
  exit 2
fi

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
  printf '[first-boss-bootstrap] ERROR: Python is required. Run scripts/bootstrap-local.sh first.\n' >&2
  exit 1
fi

if [[ "$DRY_RUN" == "1" ]]; then
  printf '[first-boss-bootstrap] Dry run: would inspect canonical Farm and active Boss prerequisites.\n'
  exit 0
fi

FIRST_BOSS_LOGIN_NAME="$LOGIN_NAME" FIRST_BOSS_DISPLAY_NAME="$DISPLAY_NAME" "$PYTHON_BIN" - <<'PY'
from __future__ import annotations

import getpass
import os
import sys

from backend.app.access_admin.admin_service import (
    AdminCommandError,
    AdminCommandErrorCode,
    AdminService,
)
from backend.app.config import AppSettings
from backend.app.database import build_database

login_name = os.environ["FIRST_BOSS_LOGIN_NAME"]
display_name = os.environ["FIRST_BOSS_DISPLAY_NAME"]

password = getpass.getpass("First Boss password: ")
confirmation = getpass.getpass("Confirm First Boss password: ")
if password != confirmation:
    print("[first-boss-bootstrap] ERROR: password confirmation did not match.", file=sys.stderr)
    raise SystemExit(1)

database = build_database(AppSettings.from_env())
try:
    with database.session() as session:
        result = AdminService(session).bootstrap_first_boss(
            login_name=login_name,
            display_name=display_name,
            password=password,
        )
    print(
        "[first-boss-bootstrap] First Boss created; "
        f"login={result.account.login_name} role={result.membership.role_preset}."
    )
except AdminCommandError as exc:
    messages = {
        AdminCommandErrorCode.FARM_NOT_INITIALIZED: (
            "canonical Farm is missing; run bash scripts/bootstrap-farm-local.sh first."
        ),
        AdminCommandErrorCode.LAST_BOSS_CONFLICT: (
            "an active Boss already exists; first-Boss bootstrap is one-shot."
        ),
        AdminCommandErrorCode.ACCOUNT_CONFLICT: "login name already exists.",
        AdminCommandErrorCode.INVALID_INPUT: "input validation failed.",
    }
    print(
        f"[first-boss-bootstrap] ERROR: {messages.get(exc.code, 'bootstrap failed without committed changes.')}",
        file=sys.stderr,
    )
    raise SystemExit(1)
finally:
    database.dispose()
PY
