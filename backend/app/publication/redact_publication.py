from __future__ import annotations

from backend.app.privacy import RedactionResult, redact_payload


def redact_bus_event(event: dict) -> RedactionResult:
    return redact_payload(event, high_risk=True)


def redact_message_envelope(envelope: dict) -> RedactionResult:
    return redact_payload(envelope, high_risk=True)


def redact_ui_feed_event(event: dict) -> RedactionResult:
    return redact_payload(event, high_risk=True)
