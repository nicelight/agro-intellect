#!/usr/bin/env python3
"""Test-only authoritative reread for the daily check-in e2e.

Reads daily check-in evidence for every seeded plant from the isolated
PostgreSQL database used by the running e2e backend, plus the matching
`daily_checkin_recorded` timeline events from the default local timeline root.
It also exposes the seed plant_key -> plant_id mapping so the spec can address
the archived/denied plants without granting them to the Engineer surface.

It is invoked by the Playwright spec to snapshot state before and after
requests so the spec can assert success persisted exactly once and denied
requests left no residue. This never modifies application code or state.

Usage: reread-checkins.py <dbname>
"""
from __future__ import annotations

import json
import pathlib
import sys
from urllib.parse import urlparse

from sqlalchemy import create_engine, text

REPO_ROOT = pathlib.Path(__file__).resolve().parents[4]
TIMELINE_PATH = REPO_ROOT / "data" / "timeline" / "timeline.jsonl"


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


def timeline_checkin_events(plant_id: str) -> int:
    if not TIMELINE_PATH.exists():
        return 0
    count = 0
    for line in TIMELINE_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if (
            record.get("event_type") == "daily_checkin_recorded"
            and record.get("plant_id") == plant_id
        ):
            count += 1
    return count


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: reread-checkins.py <dbname>", file=sys.stderr)
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
                check_ins = connection.execute(
                    text("SELECT count(*) FROM daily_checkins WHERE plant_id = :pid"),
                    {"pid": pid},
                ).scalar()
                measurements = connection.execute(
                    text("SELECT count(*) FROM manual_measurements WHERE plant_id = :pid"),
                    {"pid": pid},
                ).scalar()
                counts[pid] = {
                    "plant_key": str(plant_key),
                    "check_ins": int(check_ins or 0),
                    "measurements": int(measurements or 0),
                    "timeline_checkin_events": timeline_checkin_events(pid),
                }
    finally:
        engine.dispose()
    print(json.dumps({"dbname": dbname, "keys": keys, "counts": counts}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
