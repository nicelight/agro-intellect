#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DRY_RUN=0

usage() {
  cat <<'USAGE'
Usage: bash scripts/db-init-local.sh [--dry-run]

Creates or verifies the local PostgreSQL database target from DATABASE_URL.
Output is intentionally redacted: it does not print .env contents, passwords,
tokens, or credential-bearing database URLs.
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
      printf '[db-init] ERROR: unsupported argument: %s\n' "$arg" >&2
      usage >&2
      exit 2
      ;;
  esac
done

log() {
  printf '[db-init] %s\n' "$*"
}

fail() {
  printf '[db-init] ERROR: %s\n' "$*" >&2
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

command -v python3 >/dev/null 2>&1 || fail "python3 is required. Run scripts/bootstrap-local.sh first."
command -v psql >/dev/null 2>&1 || fail "psql is required. Install postgresql-client and retry."
command -v pg_isready >/dev/null 2>&1 || fail "pg_isready is required. Install postgresql-client and retry."

DATABASE_URL="${DATABASE_URL:-postgresql+psycopg://postgres:postgres@localhost/agro_intellect}"

mapfile -t parsed < <(DATABASE_URL="$DATABASE_URL" python3 - <<'PY'
from os import environ
from urllib.parse import unquote, urlparse

url = environ["DATABASE_URL"]
parsed = urlparse(url)
if not parsed.scheme.startswith("postgresql"):
    raise SystemExit("DATABASE_URL must use a PostgreSQL scheme")
database = parsed.path.lstrip("/")
if not database:
    raise SystemExit("DATABASE_URL must include a database name")
host = parsed.hostname or "localhost"
port = str(parsed.port or 5432)
user = unquote(parsed.username or "")
password = unquote(parsed.password or "")
if not user:
    raise SystemExit("DATABASE_URL must include a user")
redacted = f"postgresql://{user}:***@{host}:{port}/{database}"
print(host)
print(port)
print(database)
print(user)
print(password)
print(redacted)
PY
) || fail "DATABASE_URL could not be parsed. Check .env without printing it."

DB_HOST="${parsed[0]}"
DB_PORT="${parsed[1]}"
DB_NAME="${parsed[2]}"
DB_USER="${parsed[3]}"
DB_PASSWORD="${parsed[4]}"
DB_REDACTED="${parsed[5]}"

case "$DB_HOST" in
  localhost|127.0.0.1|::1)
    ;;
  *)
    fail "Only local PostgreSQL hosts are supported by this Foundation script."
    ;;
esac

log "Target database: ${DB_REDACTED}"

if [[ "$DRY_RUN" == "1" ]]; then
  log "Dry run: would check PostgreSQL readiness on ${DB_HOST}:${DB_PORT}."
  log "Dry run: would create or verify role and database idempotently."
  log "Local PostgreSQL init completed."
  exit 0
fi

if ! pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" >/dev/null 2>&1; then
  fail "PostgreSQL is not ready on ${DB_HOST}:${DB_PORT}. Start the local service and retry."
fi

psql_admin_from_url() {
  PGPASSWORD="$DB_PASSWORD" psql \
    -X -q -w -v ON_ERROR_STOP=1 -v VERBOSITY=terse \
    -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres "$@"
}

psql_admin_as_postgres_os_user() {
  sudo -n -u postgres psql \
    -X -q -v ON_ERROR_STOP=1 -v VERBOSITY=terse \
    -d postgres "$@"
}

psql_target() {
  PGPASSWORD="$DB_PASSWORD" psql \
    -X -q -w -v ON_ERROR_STOP=1 -v VERBOSITY=terse \
    -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" "$@"
}

ADMIN_MODE=""
if psql_admin_from_url -c "SELECT 1" >/dev/null 2>&1; then
  ADMIN_MODE="url"
elif command -v sudo >/dev/null 2>&1 && psql_admin_as_postgres_os_user -c "SELECT 1" >/dev/null 2>&1; then
  ADMIN_MODE="postgres-os-user"
  log "Using local postgres OS account for database setup."
else
  fail "Cannot authenticate to local PostgreSQL. Update DATABASE_URL in .env or allow passwordless sudo for the local postgres OS account."
fi

psql_admin() {
  if [[ "$ADMIN_MODE" == "url" ]]; then
    psql_admin_from_url "$@"
  else
    psql_admin_as_postgres_os_user "$@"
  fi
}

python3 - "$DB_USER" "$DB_PASSWORD" "$DB_NAME" <<'PY' | psql_admin
from sys import argv

user, password, database = argv[1:4]

def ident(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'

def literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"

role_sql = f"CREATE ROLE {ident(user)} LOGIN"
if password:
    role_sql += f" PASSWORD {literal(password)}"
print(
    "SELECT "
    + literal(role_sql)
    + " WHERE NOT EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = "
    + literal(user)
    + ")\\gexec"
)
if password:
    print(f"ALTER ROLE {ident(user)} LOGIN PASSWORD {literal(password)};")
print(
    "SELECT "
    + literal(f"CREATE DATABASE {ident(database)} OWNER {ident(user)}")
    + " WHERE NOT EXISTS (SELECT 1 FROM pg_catalog.pg_database WHERE datname = "
    + literal(database)
    + ")\\gexec"
)
PY

psql_target -c "SELECT 1" >/dev/null
log "Verified local PostgreSQL database connectivity."
log "Local PostgreSQL init completed."
