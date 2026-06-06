"""Standard API error envelope and error codes."""

from __future__ import annotations

from enum import Enum
from typing import Any


class ErrorCode(str, Enum):
    INVALID_REQUEST = "invalid_request"
    INVALID_SESSION = "invalid_session"
    PERMISSION_DENIED = "permission_denied"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    ARCHIVED_RESOURCE = "archived_resource"
    VALIDATION_FAILED = "validation_failed"
    UPLOAD_REJECTED = "upload_rejected"
    INVALID_CONFIG = "invalid_config"
    APPROVAL_REQUIRED = "approval_required"
    SAFETY_GATE_BLOCKED = "safety_gate_blocked"
    STALE_OR_MISSING_EVIDENCE = "stale_or_missing_evidence"
    RATE_LIMITED = "rate_limited"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    INTERNAL_ERROR = "internal_error"


class AppError(Exception):
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        details: dict[str, Any] | None = None,
        request_ref: str | None = None,
        next_actions: list[str] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.details = details or {}
        self.request_ref = request_ref
        self.next_actions = next_actions or []
        super().__init__(message)


def error_response(error: AppError) -> dict[str, Any]:
    return {
        "error": {
            "code": error.code.value,
            "message": error.message,
            "details": error.details,
            "request_ref": error.request_ref or "req_redacted_or_trace_ref",
            "next_valid_actions": error.next_actions,
        }
    }
