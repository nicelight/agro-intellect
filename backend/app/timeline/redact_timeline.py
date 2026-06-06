from __future__ import annotations

from backend.app.privacy import RedactionResult, redact_payload


def redact_timeline_entry(entry: dict) -> RedactionResult:
    return redact_payload(entry, high_risk=True)
