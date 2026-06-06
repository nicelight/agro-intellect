from __future__ import annotations

from backend.app.privacy import RedactionResult, redact_payload


class ObservationWriter:
    def record_observation(
        self,
        observation: dict,
        request_ref: str | None = None,
    ) -> RedactionResult:
        result = redact_payload(observation, high_risk=True)
        if result.status == "rejected":
            return result
        return result

    def record_trace(self, trace_entry: dict) -> RedactionResult:
        return redact_payload(trace_entry, high_risk=True)
