#!/usr/bin/env python3
"""Test-only authoritative reread for the local photo upload e2e.

Reads photo catalog evidence for every seeded plant from the isolated
PostgreSQL database used by the running e2e backend, the isolated photo
artifact root recovered from the e2e backend environment, and the matching
`photo_accepted` timeline events from the isolated timeline root. It also
exposes the seed plant_key -> plant_id mapping so the spec can address the
archived/denied plants without granting them to the Engineer surface.

It is invoked by the Playwright spec to snapshot state before and after
requests so the spec can assert a success persisted exactly once (one catalog
row plus exactly the matching original + manifest artifact files), that denied
requests left no accepted artifact or catalog row, and that event refs match a
real timeline event. This never modifies application code or state.

Usage: reread-photos.py <dbname> <artifact_root> <timeline_root>
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


def timeline_photo_events(plant_id: str, timeline_root: pathlib.Path) -> int:
    path = timeline_root / "timeline.jsonl"
    if not path.exists():
        return 0
    count = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if (
            record.get("event_type") == "photo_accepted"
            and record.get("plant_id") == plant_id
        ):
            count += 1
    return count


def list_artifacts(artifact_root: pathlib.Path) -> list[dict[str, object]]:
    if not artifact_root.exists():
        return []
    found: list[dict[str, object]] = []
    for path in sorted(artifact_root.rglob("*")):
        if not path.is_file():
            continue
        found.append(
            {
                "ref": str(path.relative_to(artifact_root)).replace("\\", "/"),
                "size": path.stat().st_size,
            }
        )
    return found


def main() -> int:
    if len(sys.argv) != 4:
        print(
            "usage: reread-photos.py <dbname> <artifact_root> <timeline_root>",
            file=sys.stderr,
        )
        return 2
    dbname, artifact_root_str, timeline_root_str = sys.argv[1:4]
    artifact_root = pathlib.Path(artifact_root_str)
    timeline_root = pathlib.Path(timeline_root_str)
    engine = create_engine(target_dsn(dbname), pool_pre_ping=True)
    keys: dict[str, str] = {}
    catalogs: dict[str, list[dict[str, object]]] = {}
    timeline_counts: dict[str, int] = {}
    try:
        with engine.connect() as connection:
            plant_rows = connection.execute(
                text("SELECT plant_id, plant_key FROM plants ORDER BY plant_key")
            ).all()
            for plant_id, plant_key in plant_rows:
                pid = str(plant_id)
                keys[str(plant_key)] = pid
                rows = connection.execute(
                    text(
                        "SELECT photo_id, photo_type, content_type, size_bytes, "
                        "sha256, original_file_ref, manifest_ref, event_refs, "
                        "local_only, can_train_on FROM photo_catalog_items "
                        "WHERE plant_id = :pid ORDER BY uploaded_at"
                    ),
                    {"pid": pid},
                ).all()
                items = []
                for row in rows:
                    items.append(
                        {
                            "photo_id": str(row.photo_id),
                            "photo_type": str(row.photo_type),
                            "content_type": str(row.content_type),
                            "size_bytes": int(row.size_bytes),
                            "sha256": str(row.sha256),
                            "original_file_ref": str(row.original_file_ref),
                            "manifest_ref": str(row.manifest_ref),
                            "event_refs": (row.event_refs or {}),
                            "local_only": bool(row.local_only),
                            "can_train_on": bool(row.can_train_on),
                        }
                    )
                catalogs[pid] = items
                timeline_counts[pid] = timeline_photo_events(pid, timeline_root)
    finally:
        engine.dispose()
    print(
        json.dumps(
            {
                "dbname": dbname,
                "keys": keys,
                "catalogs": catalogs,
                "artifacts": list_artifacts(artifact_root),
                "timeline_counts": timeline_counts,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
