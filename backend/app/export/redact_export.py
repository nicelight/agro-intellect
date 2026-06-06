from __future__ import annotations

from backend.app.privacy import RedactionResult, redact_payload


def redact_export_payload(payload: dict) -> RedactionResult:
    return redact_payload(payload, high_risk=True)
