#!/usr/bin/env python3
"""Test-only authoritative reread for the Plant-feed e2e (TASK-086).

Reads the isolated PostgreSQL database used by the running e2e backend and
snapshots authoritative Feed/presentation state per Plant: plant keys, UI Feed
event counts grouped by display_kind, the seeded event IDs with their
presentation-only flags, and the total Agent Bus event count. The spec uses
this snapshot before/after feed reads, pagination, retry, and reloads to prove
feed reads leave no mutation residue, never publish to Bus, and never flip the
`visible_to_agents`/`consumable_by_agents` flags. It never modifies
application code or state.

Usage: reread-plant-feed.py <dbname>
"""
from __future__ import annotations

import json
import pathlib
import sys
from urllib.parse import urlparse

from sqlalchemy import create_engine, text

REPO_ROOT = pathlib.Path(__file__).resolve().parents[4]

SEEDED_IDS = [
    "10000000-0000-4000-8000-000000000001",
    "10000000-0000-4000-8000-000000000101",
    "10000000-0000-4000-8000-000000000104",
    "10000000-0000-4000-8000-000000000105",
    "10000000-0000-4000-8000-000000000106",
    "10000000-0000-4000-8000-000000000107",
    "10000000-0000-4000-8000-000000000108",
    "10000000-0000-4000-8000-000000000109",
    "10000000-0000-4000-8000-00000000010a",
] + [
    f"20000000-0000-4000-8000-0000000000{n:02d}"
    for n in range(1, 25)
]


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
        print("usage: reread-plant-feed.py <dbname>", file=sys.stderr)
        return 2
    dbname = sys.argv[1]
    engine = create_engine(target_dsn(dbname), pool_pre_ping=True)
    keys: dict[str, str] = {}
    counts: dict[str, dict[str, int]] = {}
    flags: dict[str, dict[str, object]] = {}
    bus_total = 0
    try:
        with engine.connect() as connection:
            plant_rows = connection.execute(
                text("SELECT plant_id, plant_key FROM plants ORDER BY plant_key")
            ).all()
            for plant_id, plant_key in plant_rows:
                pid = str(plant_id)
                keys[str(plant_key)] = pid
                kind_rows = connection.execute(
                    text(
                        "SELECT display_kind, count(*) FROM ui_feed_events "
                        "WHERE plant_id = :pid GROUP BY display_kind"
                    ),
                    {"pid": pid},
                ).all()
                counts[pid] = {
                    str(kind): int(total) for kind, total in kind_rows
                }
            for event_id in SEEDED_IDS:
                row = connection.execute(
                    text(
                        "SELECT visible_to_agents, consumable_by_agents "
                        "FROM ui_feed_events WHERE ui_event_id = :eid"
                    ),
                    {"eid": event_id},
                ).first()
                if row is not None:
                    flags[event_id] = {
                        "visible_to_agents": bool(row[0]),
                        "consumable_by_agents": bool(row[1]),
                    }
            bus_total = int(
                connection.execute(
                    text("SELECT count(*) FROM agent_bus_events")
                ).scalar()
                or 0
            )
    finally:
        engine.dispose()
    print(
        json.dumps(
            {
                "dbname": dbname,
                "keys": keys,
                "counts": counts,
                "seeded_flags": flags,
                "bus_total": bus_total,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
