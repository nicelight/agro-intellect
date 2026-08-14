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
_URL_SCHEME_RE = re.compile(r"(?<!\w)[\w\+]+://")
_CLEAN_USERINFO_RE = re.compile(r"[^@\s/]+")
_USERINFO_AT_RE = re.compile(r"[^:/]*:[^@]*@")
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


_RENDER_FAILURE = "redaction failed: value cannot be rendered as text"


def _render_text(value: Any) -> str:
    try:
        return str(value)
    except Exception:
        raise ValueError(_RENDER_FAILURE) from None


def is_sensitive_key(key: str) -> bool:
    return bool(_SENSITIVE_KEY_RE.search(key.strip()))


def _host_qualified_at(text: str, start: int, window_end: int) -> int:
    """Return the first '@' whose following host region contains no further '@'.

    Mirrors the app's own URL parser (username/password end at the separator
    '@' whose tail runs to the path delimiter), while treating any earlier
    '@' as part of a hostile userinfo span.
    """
    pos = text.find("@", start, window_end)
    while pos >= 0:
        host_end = len(text)
        for delim in ("/", "?", "#"):
            idx = text.find(delim, pos + 1, window_end)
            if idx >= 0 and idx < host_end:
                host_end = idx
        if text.find("@", pos + 1, host_end) < 0:
            return pos
        pos = text.find("@", pos + 1, window_end)
    return -1


def _mask_userinfo(userinfo: str) -> str:
    if ":" not in userinfo:
        return REDACTION
    username, _, password = userinfo.partition(":")
    if _CLEAN_USERINFO_RE.fullmatch(password) and _CLEAN_USERINFO_RE.fullmatch(username):
        return f"{username}:{REDACTION}"
    return REDACTION


def redact_url_credentials(value: Any) -> str:
    text = _render_text(value)
    parts: list[str] = []
    cursor = 0
    for scheme in _URL_SCHEME_RE.finditer(text):
        if scheme.start() < cursor:
            continue
        scheme_end = scheme.end()
        if _USERINFO_AT_RE.match(text, scheme_end) is None:
            continue
        sep = _host_qualified_at(text, scheme_end, len(text))
        if sep < 0:
            continue
        userinfo = text[scheme_end:sep]
        parts.append(text[cursor:scheme.start()])
        parts.append(scheme.group(0))
        parts.append(_mask_userinfo(userinfo))
        parts.append("@")
        cursor = sep + 1
    parts.append(text[cursor:])
    return "".join(parts)


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
    text = _render_text(value)
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
    string_mapping = {key: _render_text(value) for key, value in mapping.items()}
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
