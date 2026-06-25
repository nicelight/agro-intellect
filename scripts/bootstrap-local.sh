#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DRY_RUN=0

usage() {
  cat <<'USAGE'
Usage: bash scripts/bootstrap-local.sh [--dry-run]

Bootstraps the local Linux Mint backend environment without printing .env
contents, credentials, tokens, or database URLs.
USAGE
}

redact() {
  local value="$*"
  if command -v python3 >/dev/null 2>&1; then
    AGRO_REDACT_TEXT="$value" PYTHONPATH="$PROJECT_ROOT/backend/app/core${PYTHONPATH:+:$PYTHONPATH}" python3 - <<'PY' 2>/dev/null && return 0
from os import environ
from redaction import redact_text

print(redact_text(environ.get("AGRO_REDACT_TEXT", ""), environ=environ), end="")
PY
  fi
  printf '%s' "$value" \
    | sed -E 's#://([^:/@[:space:]]+):([^@[:space:]/]+)@#://\1:***@#g; s#([A-Za-z_][A-Za-z0-9_-]*(PASSWORD|PASSWD|PWD|TOKEN|SECRET|API[_-]?KEY|AUTH|AUTHORIZATION|CREDENTIAL|CREDENTIALS|DATABASE[_-]?URL|DB[_-]?URL|DSN|PRIVATE[_-]?KEY)[A-Za-z0-9_-]*[[:space:]]*[:=][[:space:]]*)[^[:space:],;]+#\1***#Ig'
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
      printf '[bootstrap] ERROR: %s\n' "$(redact "unsupported argument: $arg")" >&2
      usage >&2
      exit 2
      ;;
  esac
done

log() {
  printf '[bootstrap] %s\n' "$(redact "$*")"
}

warn() {
  printf '[bootstrap] WARN: %s\n' "$(redact "$*")" >&2
}

fail() {
  printf '[bootstrap] ERROR: %s\n' "$(redact "$*")" >&2
  exit 1
}

cd "$PROJECT_ROOT"

command -v python3 >/dev/null 2>&1 || fail "python3 is required. Install Python 3.11+ on Linux Mint and retry."

python3 - <<'PY' || fail "Python 3.11+ is required. Install a supported Python version and retry."
import sys
raise SystemExit(0 if sys.version_info >= (3, 11) else 1)
PY

if [[ "$DRY_RUN" == "1" ]]; then
  log "Dry run: would create or reuse .venv and install project/test dependencies."
else
  if [[ ! -d ".venv" ]]; then
    log "Creating local Python virtual environment at .venv."
    python3 -m venv .venv
  else
    log "Reusing existing local Python virtual environment at .venv."
  fi

  log "Installing project and test dependencies into .venv."
  .venv/bin/python -m pip install --upgrade pip >/dev/null
  .venv/bin/python -m pip install -e ".[test]"
fi

if [[ ! -f ".env.example" ]]; then
  fail ".env.example is missing; cannot prepare local environment."
fi

if [[ -f ".env" ]]; then
  log ".env already exists; leaving it unchanged."
elif [[ "$DRY_RUN" == "1" ]]; then
  log "Dry run: would create .env from .env.example without printing contents."
else
  cp .env.example .env
  chmod 600 .env
  log "Created .env from .env.example without printing contents."
fi

if command -v psql >/dev/null 2>&1 && command -v pg_isready >/dev/null 2>&1; then
  log "PostgreSQL client tools detected."
else
  warn "PostgreSQL client tools not found. Install 'postgresql-client' on Linux Mint before running scripts/db-init-local.sh."
fi

runtime_dirs=(
  "data"
  "data/artifacts"
  "data/timeline"
  "data/tmp"
  "data/smoke"
)

for dir in "${runtime_dirs[@]}"; do
  if [[ "$DRY_RUN" == "1" ]]; then
    log "Dry run: would ensure local runtime directory ${dir}."
  else
    mkdir -p "$dir"
  fi
done

if [[ "$DRY_RUN" != "1" ]]; then
  log "Ensured local runtime directories."
fi

log "Linux Mint local bootstrap completed."
