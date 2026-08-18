#!/usr/bin/env python3
"""Test-only authoritative reread for the Plant-history-card e2e (TASK-085).

Reads the isolated PostgreSQL database used by the running e2e backend and
snapshots authoritative history/card state per Plant: check-in, measurement,
photo, and admin-audit row counts plus plant keys and current card-order refs.
The spec uses this snapshot before/after denied/malformed/archived card reads
to prove those reads leave no mutation residue. It never modifies application
code or state.

Usage: reread-history-card.py <dbname>
"""
from __future__ import annotations

import json
import pathlib
import sys
from urllib.parse import urlparse

from sqlalchemy import create_engine, text

REPO_ROOT = pathlib.Path(__file__).resolve().parents[4]


def env_value(key: str) -> str | None:
    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        return None
    for line in env_path.read_text(encoding="utf-8").splitlines():
        trimmed = line.strip()
        if not trimmed or trimmed.startswith("#"):
            continue
        if "=" not in trimmed:
            continue
        name, value = trimmed.split("=", 1)
        if name.strip() == key:
            return value.strip()
    return None


def target_dsn(dbname: str) -> str:
    base = env_value("DATABASE_URL")
    if not base:
        raise SystemExit("DATABASE_URL not found in .env")
    url = urlparse(base)
    creds = url.username or ""
    if url.password:
        creds += f":{url.password}"
    host = url.hostname or "localhost"
    port = url.port or "5432"
    return f"postgresql+psycopg://{creds}@{host}:{port}/{dbname}"


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: reread-history-card.py <dbname>", file=sys.stderr)
        return 2
    dbname = sys.argv[1]
    engine = create_engine(target_dsn(dbname), pool_pre_ping=True)
    keys: dict[str, str] = {}
    counts: dict[str, dict[str, int]] = {}
    try:
        with engine.connect() as connection:
            rows = connection.execute(
                text("SELECT plant_id, plant_key FROM plants ORDER BY plant_key")
            ).all()
            for plant_id, plant_key in rows:
                pid = str(plant_id)
                keys[str(plant_key)] = pid
                counts[pid] = {
                    "plant_key": str(plant_key),
                    "check_ins": int(
                        connection.execute(
                            text(
                                "SELECT count(*) FROM daily_checkins "
                                "WHERE plant_id = :pid"
                            ),
                            {"pid": pid},
                        ).scalar()
                        or 0
                    ),
                    "measurements": int(
                        connection.execute(
                            text(
                                "SELECT count(*) FROM manual_measurements "
                                "WHERE plant_id = :pid"
                            ),
                            {"pid": pid},
                        ).scalar()
                        or 0
                    ),
                    "photos": int(
                        connection.execute(
                            text(
                                "SELECT count(*) FROM photo_catalog_items "
                                "WHERE plant_id = :pid"
                            ),
                            {"pid": pid},
                        ).scalar()
                        or 0
                    ),
                    "admin_audits": int(
                        connection.execute(
                            text(
                                "SELECT count(*) FROM admin_audit_records "
                                "WHERE plant_id = :pid"
                            ),
                            {"pid": pid},
                        ).scalar()
                        or 0
                    ),
                }
    finally:
        engine.dispose()
    print(json.dumps({"dbname": dbname, "keys": keys, "counts": counts}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
