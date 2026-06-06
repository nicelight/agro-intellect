"""Security helpers for backend-owned auth material."""

from backend.app.privacy import (
    DEFAULT_REDACTION_POLICY,
    RedactionPolicy,
    RedactionResult,
    redact_payload,
    redact_text,
)
from backend.app.security.cors_origin import (
    validate_cors_config,
    validate_cors_origin,
)
from backend.app.security.session_refs import (
    AUTH_MATERIAL_REDACTION_MARKER,
    auth_provenance_ref_from_hash,
    generate_session_secret,
    hash_session_secret,
    redact_auth_payload,
    redacted_request_ref,
    session_ref_from_hash,
)

redact_secret_payload = redact_payload
redact_secret_text = redact_text

__all__ = [
    "AUTH_MATERIAL_REDACTION_MARKER",
    "DEFAULT_REDACTION_POLICY",
    "RedactionPolicy",
    "RedactionResult",
    "auth_provenance_ref_from_hash",
    "generate_session_secret",
    "hash_session_secret",
    "redact_auth_payload",
    "redact_secret_payload",
    "redact_secret_text",
    "redacted_request_ref",
    "session_ref_from_hash",
    "validate_cors_config",
    "validate_cors_origin",
]