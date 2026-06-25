from __future__ import annotations

from collections.abc import Iterable, Mapping
from os import environ as os_environ
import re
from typing import Any


REDACTION = "***"

_SENSITIVE_KEY_RE = re.compile(
    r"(?:^|[_-])(?:password|passwd|pwd|token|secret|api[_-]?key|"
    r"auth|authorization|credentials?|database[_-]?url|db[_-]?url|dsn|"
    r"private[_-]?key)(?:$|[_-])",
    re.IGNORECASE,
)
_URL_WITH_CREDS_RE = re.compile(
    r"(?P<scheme>\b[a-z][a-z0-9+.-]*://)(?P<userinfo>[^@\s/]+)@",
    re.IGNORECASE,
)
_AUTH_HEADER_RE = re.compile(
    r"\b(?P<key>Authorization\s*[:=]\s*)(?:Bearer|Basic)\s+[^\s,;]+",
    re.IGNORECASE,
)
_AUTH_SCHEME_RE = re.compile(
    r"\b(?P<scheme>Bearer|Basic)\s+[A-Za-z0-9._~+/=-]+",
    re.IGNORECASE,
)
_ASSIGNMENT_RE = re.compile(
    r"(?P<prefix>(?<![A-Za-z0-9_-])--?)?"
    r"(?P<key>(?=[A-Za-z_][A-Za-z0-9_-]*\b)"
    r"(?=[A-Za-z0-9_-]*(?:PASSWORD|PASSWD|PWD|TOKEN|SECRET|API[_-]?KEY|"
    r"AUTH(?:ORIZATION)?|CREDENTIALS?|DATABASE[_-]?URL|DB[_-]?URL|DSN|"
    r"PRIVATE[_-]?KEY))[A-Za-z_][A-Za-z0-9_-]*)"
    r"(?P<sep>\s*[:=]\s*)"
    r"(?P<value>\"[^\"\n]*\"|'[^'\n]*'|[^\s,;]+)",
    re.IGNORECASE,
)


def is_sensitive_key(key: str) -> bool:
    return bool(_SENSITIVE_KEY_RE.search(key.strip()))


def redact_url_credentials(value: Any) -> str:
    text = str(value)

    def replace(match: re.Match[str]) -> str:
        userinfo = match.group("userinfo")
        if ":" in userinfo:
            username = userinfo.split(":", 1)[0]
            return f"{match.group('scheme')}{username}:{REDACTION}@"
        return f"{match.group('scheme')}{REDACTION}@"

    return _URL_WITH_CREDS_RE.sub(replace, text)


def _iter_secret_values(
    environ: Mapping[str, str] | None,
    extra_secrets: Iterable[str] | None,
) -> list[str]:
    values: list[str] = []
    source = os_environ if environ is None else environ
    for key, value in source.items():
        if is_sensitive_key(key) and _redactable_value(value):
            values.append(str(value))
    if extra_secrets is not None:
        for value in extra_secrets:
            if _redactable_value(value):
                values.append(str(value))
    return sorted(set(values), key=len, reverse=True)


def _redactable_value(value: Any) -> bool:
    text = str(value)
    return bool(text) and text != REDACTION and len(text) >= 3


def redact_text(
    value: Any,
    *,
    environ: Mapping[str, str] | None = None,
    extra_secrets: Iterable[str] | None = None,
) -> str:
    text = redact_url_credentials(value)
    text = _AUTH_HEADER_RE.sub(r"\g<key>" + REDACTION, text)
    text = _AUTH_SCHEME_RE.sub(r"\g<scheme> " + REDACTION, text)
    text = _ASSIGNMENT_RE.sub(_redact_assignment, text)

    for secret in _iter_secret_values(environ, extra_secrets):
        text = text.replace(secret, REDACTION)

    return text


def _redact_assignment(match: re.Match[str]) -> str:
    if not is_sensitive_key(match.group("key")):
        return match.group(0)
    return (
        f"{match.group('prefix') or ''}"
        f"{match.group('key')}{match.group('sep')}{REDACTION}"
    )


def redact_mapping(mapping: Mapping[str, Any]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    string_mapping = {key: str(value) for key, value in mapping.items()}
    for key, value in mapping.items():
        if is_sensitive_key(key):
            redacted[key] = REDACTION if _redactable_value(value) else value
        elif isinstance(value, str):
            redacted[key] = redact_text(value, environ=string_mapping)
        else:
            redacted[key] = value
    return redacted


__all__ = [
    "REDACTION",
    "is_sensitive_key",
    "redact_mapping",
    "redact_text",
    "redact_url_credentials",
]
