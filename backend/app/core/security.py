from __future__ import annotations

from collections.abc import Iterable
import hashlib
import hmac
import re
import secrets
from typing import Any

from .redaction import REDACTION, redact_text


SESSION_COOKIE_NAME = "agro_intellect_session"
SESSION_TOKEN_BYTES = 32
SESSION_TOKEN_MIN_LENGTH = 43
SESSION_TOKEN_HASH_LENGTH = 64

_SESSION_TOKEN_RE = re.compile(
    rf"[A-Za-z0-9_-]{{{SESSION_TOKEN_MIN_LENGTH},}}\Z"
)
_SESSION_TOKEN_HASH_RE = re.compile(
    rf"[0-9a-f]{{{SESSION_TOKEN_HASH_LENGTH}}}\Z"
)
_COOKIE_HEADER_RE = re.compile(
    r"(?P<name>\b(?:Set-Cookie|Cookie)\s*:\s*)[^\r\n]*",
    re.IGNORECASE,
)
_COOKIE_ASSIGNMENT_RE = re.compile(
    rf"(?P<name>\b(?:cookie|set_cookie|{re.escape(SESSION_COOKIE_NAME)})"
    r"\s*[:=]\s*)(?:\"[^\"\r\n]*\"|'[^'\r\n]*'|[^\s,;]+)",
    re.IGNORECASE,
)


def generate_session_token() -> str:
    """Return a URL-safe opaque token backed by 256 random bits."""

    return secrets.token_urlsafe(SESSION_TOKEN_BYTES)


def is_valid_session_token(raw_token: object) -> bool:
    """Return whether a presented token has the generated URL-safe shape."""

    return isinstance(raw_token, str) and bool(_SESSION_TOKEN_RE.fullmatch(raw_token))


def hash_session_token(raw_token: str) -> str:
    """Return the lowercase SHA-256 digest persisted for a raw session token."""

    if not is_valid_session_token(raw_token):
        raise ValueError("Invalid session token.")
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def is_valid_session_token_hash(token_hash: object) -> bool:
    """Return whether a stored token digest has the canonical SHA-256 shape."""

    return isinstance(token_hash, str) and bool(
        _SESSION_TOKEN_HASH_RE.fullmatch(token_hash)
    )


def verify_session_token(raw_token: object, stored_token_hash: object) -> bool:
    """Fail closed and compare a presented token digest in constant time."""

    if not is_valid_session_token(raw_token):
        return False
    if not is_valid_session_token_hash(stored_token_hash):
        return False

    presented_token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    return hmac.compare_digest(presented_token_hash, stored_token_hash)


def redact_auth_material(
    value: Any,
    *,
    secret_values: Iterable[str] = (),
) -> str:
    """Redact structured auth fields plus explicitly supplied secret values."""

    text = redact_text(value, extra_secrets=secret_values)
    text = _COOKIE_HEADER_RE.sub(r"\g<name>" + REDACTION, text)
    return _COOKIE_ASSIGNMENT_RE.sub(r"\g<name>" + REDACTION, text)


__all__ = [
    "SESSION_COOKIE_NAME",
    "SESSION_TOKEN_BYTES",
    "SESSION_TOKEN_HASH_LENGTH",
    "SESSION_TOKEN_MIN_LENGTH",
    "generate_session_token",
    "hash_session_token",
    "is_valid_session_token",
    "is_valid_session_token_hash",
    "redact_auth_material",
    "verify_session_token",
]
