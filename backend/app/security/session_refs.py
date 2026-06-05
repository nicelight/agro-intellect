"""Session hashing and narrow auth-material redaction helpers.

@docs .memory-bank/tech-specs/FT-017-local-privacy-deployment-controls-and-secret-redaction.md
"""

from __future__ import annotations

import hashlib
import re
import secrets
from collections.abc import Mapping, Sequence
from typing import Any

AUTH_MATERIAL_REDACTION_MARKER = "[REDACTED_TOKEN]"
SESSION_SECRET_MIN_LENGTH = 32
SESSION_SECRET_MAX_LENGTH = 4096
_SESSION_SECRET_PATTERN = re.compile(r"^[A-Za-z0-9_.~=-]+$")
_SENSITIVE_KEY_PATTERN = re.compile(
    r"(authorization|bearer|cookie|csrf|password|session|secret|token|api[_-]?key|credential)",
    re.IGNORECASE,
)
_INLINE_TOKEN_PATTERN = re.compile(
    r"\b(Bearer\s+)?[A-Za-z0-9_\-.~=/+]{32,}\b",
    re.IGNORECASE,
)


def generate_session_secret(num_bytes: int = 32) -> str:
    return secrets.token_urlsafe(num_bytes)


def is_well_formed_session_secret(raw_secret: str) -> bool:
    if not isinstance(raw_secret, str):
        return False
    if not (SESSION_SECRET_MIN_LENGTH <= len(raw_secret) <= SESSION_SECRET_MAX_LENGTH):
        return False
    return bool(_SESSION_SECRET_PATTERN.fullmatch(raw_secret))


def hash_session_secret(raw_secret: str, *, pepper: str = "") -> str:
    if not is_well_formed_session_secret(raw_secret):
        raise ValueError("session secret is malformed")
    digest = hashlib.sha256()
    digest.update(pepper.encode("utf-8"))
    digest.update(raw_secret.encode("utf-8"))
    return digest.hexdigest()


def session_ref_from_hash(session_hash: str) -> str:
    _require_sha256_hex(session_hash)
    return f"sess_ref_{session_hash[:16]}"


def auth_provenance_ref_from_hash(session_hash: str) -> str:
    _require_sha256_hex(session_hash)
    return f"auth_ref_{session_hash[16:32]}"


def redacted_request_ref(seed: str) -> str:
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return f"req_ref_{digest[:16]}"


def redact_auth_payload(
    payload: Any,
    *,
    sensitive_values: Sequence[str] = (),
) -> Any:
    """Return a copy with narrow auth/session material redacted.

    This is intentionally not the full shared detector registry; TASK-011 owns that.
    """

    sensitive_set = {value for value in sensitive_values if value}
    if isinstance(payload, Mapping):
        return {
            key: (
                AUTH_MATERIAL_REDACTION_MARKER
                if _is_sensitive_key(str(key))
                else redact_auth_payload(value, sensitive_values=tuple(sensitive_set))
            )
            for key, value in payload.items()
        }
    if isinstance(payload, list):
        return [redact_auth_payload(value, sensitive_values=tuple(sensitive_set)) for value in payload]
    if isinstance(payload, tuple):
        return tuple(
            redact_auth_payload(value, sensitive_values=tuple(sensitive_set))
            for value in payload
        )
    if isinstance(payload, str):
        if payload in sensitive_set:
            return AUTH_MATERIAL_REDACTION_MARKER
        redacted = payload
        for value in sensitive_set:
            redacted = redacted.replace(value, AUTH_MATERIAL_REDACTION_MARKER)
        return _INLINE_TOKEN_PATTERN.sub(AUTH_MATERIAL_REDACTION_MARKER, redacted)
    return payload


def _is_sensitive_key(key: str) -> bool:
    return bool(_SENSITIVE_KEY_PATTERN.search(key))


def _require_sha256_hex(value: str) -> None:
    if not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{64}", value):
        raise ValueError("expected sha256 hex digest")
