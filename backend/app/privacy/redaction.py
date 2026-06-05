"""Deterministic shared secret redaction foundation.

The functions in this module are intentionally integration-free. Later tasks can call
them before logs, traces, exports, Bus events, UI feed projection, or agent context
assembly without coupling this foundation to those surfaces.

@docs .memory-bank/tech-specs/FT-017-local-privacy-deployment-controls-and-secret-redaction.md
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

DEFAULT_SECRET_MARKER = "[REDACTED_SECRET]"
UncertainPayloadStrategy = Literal["reject", "truncate"]


@dataclass(frozen=True)
class RedactionFinding:
    """Metadata about a redacted value without retaining the raw secret."""

    secret_type: str
    marker: str
    ref: str
    detector: str


@dataclass(frozen=True)
class RedactionResult:
    """Result returned by shared redaction entrypoints."""

    value: Any
    status: Literal["no_sensitive_fields", "redacted", "rejected", "truncated"]
    findings: tuple[RedactionFinding, ...] = ()
    action: Literal["allow", "reject", "truncate"] = "allow"
    reason: str | None = None

    @property
    def redacted(self) -> bool:
        return bool(self.findings)


@dataclass(frozen=True)
class RedactionPolicy:
    """Configurable detector inputs for user-provided secret-like text."""

    configured_secret_values: tuple[str, ...] = ()
    configured_secret_patterns: tuple[re.Pattern[str], ...] = ()
    ref_salt: str = "agro-intellect-redaction-v1"
    truncated_marker: str = "[TRUNCATED_HIGH_RISK_PAYLOAD]"
    max_string_length: int = 20_000


DEFAULT_REDACTION_POLICY = RedactionPolicy()

_SAFE_REF_KEYS = {
    "auth_provenance_ref",
    "request_ref",
    "safe_ref",
    "session_ref",
    "trace_ref",
}
_SENSITIVE_KEY_PATTERN = re.compile(
    r"(^|[_-])("
    r"authorization|bearer|cookie|csrf|credential|db_password|password|private_key|"
    r"refresh_token|reset_token|secret|session_id|session_secret|session_token|token|"
    r"api_key|apikey|access_key|webhook_secret|connector_secret|client_secret"
    r")($|[_-])",
    re.IGNORECASE,
)
_CONNECTION_STRING_KEY_PATTERN = re.compile(
    r"(^|[_-])(database_url|db_url|dsn|connection_string)($|[_-])",
    re.IGNORECASE,
)
_PUBLIC_KEY_PATTERN = re.compile(r"(^|[_-])public_key($|[_-])", re.IGNORECASE)

_PRIVATE_KEY_BLOCK_PATTERN = re.compile(
    r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----.*?-----END [A-Z0-9 ]*PRIVATE KEY-----",
    re.IGNORECASE | re.DOTALL,
)
_PRIVATE_KEY_BEGIN_PATTERN = re.compile(
    r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----",
    re.IGNORECASE,
)
_CREDENTIAL_URL_PATTERN = re.compile(
    r"\b(?P<scheme>(?:postgres(?:ql)?|mysql|mariadb|mongodb(?:\+srv)?|redis|amqp|"
    r"rabbitmq)://)(?P<user>[^:\s/@]+):(?P<password>[^@\s/]+)@(?P<rest>[^\s'\"<>]+)",
    re.IGNORECASE,
)
_AUTHORIZATION_BEARER_PATTERN = re.compile(
    r"\b(?P<prefix>Authorization\s*[:=]\s*Bearer\s+)(?P<token>[^\s,;]+)",
    re.IGNORECASE,
)
_BARE_BEARER_PATTERN = re.compile(
    r"\b(?P<prefix>Bearer\s+)(?P<token>[A-Za-z0-9._~+/=-]{20,})\b",
    re.IGNORECASE,
)
_COOKIE_HEADER_PATTERN = re.compile(
    r"\b(?P<prefix>(?:Cookie|Set-Cookie)\s*[:=]\s*)(?P<cookie>[^\n\r]+)",
    re.IGNORECASE,
)
_SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"(?im)(?P<prefix>\b(?:"
    r"access[_-]?token|api[_-]?key|apikey|client[_-]?secret|"
    r"connector[_-]?secret|csrf[_-]?token|password|private[_-]?key|"
    r"refresh[_-]?token|reset[_-]?token|secret|session[_-]?id|session[_-]?secret|"
    r"session[_-]?token|webhook[_-]?secret"
    r")\s*[:=]\s*)(?P<quote>['\"]?)(?P<value>[^\s,'\";]+)(?P=quote)",
)
_ENV_SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"(?m)^(?P<prefix>\s*[A-Z][A-Z0-9_]*(?:SECRET|TOKEN|PASSWORD|CREDENTIAL|"
    r"PRIVATE_KEY|API_KEY|ACCESS_KEY)[A-Z0-9_]*\s*=\s*)"
    r"(?P<quote>['\"]?)(?P<value>[^'\"\n#]+)(?P=quote)",
)
_QUERY_SECRET_PATTERN = re.compile(
    r"(?P<prefix>[?&](?:access_token|api_key|apikey|auth|password|refresh_token|"
    r"secret|signature|token|webhook_secret)=)(?P<value>[^&#\s]+)",
    re.IGNORECASE,
)
_PROVIDER_KEY_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("api_key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}\b")),
    ("api_key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("api_key", re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b")),
    ("connector_secret", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{20,}\b")),
    ("connector_secret", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")),
    ("webhook_secret", re.compile(r"\bwhsec_[A-Za-z0-9]{16,}\b")),
)
_SESSION_ID_PATTERN = re.compile(r"\bsession_(?!ref\b)[A-Za-z0-9_-]{24,}\b")
_GENERIC_SECRET_KEYWORD_PATTERN = re.compile(
    r"api|auth|bearer|client|connector|cookie|credential|csrf|database|db|key|"
    r"password|private|refresh|reset|secret|session|token|webhook",
    re.IGNORECASE,
)


def stable_secret_ref(
    value: str,
    *,
    secret_type: str = "secret",
    policy: RedactionPolicy = DEFAULT_REDACTION_POLICY,
) -> str:
    """Return a stable non-reversible ref for correlation without storing the raw value."""

    digest = hashlib.sha256()
    digest.update(policy.ref_salt.encode("utf-8"))
    digest.update(b":")
    digest.update(secret_type.encode("utf-8"))
    digest.update(b":")
    digest.update(value.encode("utf-8", errors="surrogatepass"))
    return f"redacted_{secret_type}_{digest.hexdigest()[:16]}"


def redact_text(
    text: str,
    *,
    policy: RedactionPolicy = DEFAULT_REDACTION_POLICY,
    high_risk: bool = False,
    uncertain_strategy: UncertainPayloadStrategy = "reject",
) -> RedactionResult:
    """Redact secret-like content from text.

    When `high_risk=True`, incomplete private-key material or oversized strings are
    rejected/truncated instead of being returned raw.
    """

    if not isinstance(text, str):
        raise TypeError("redact_text expects a string")

    redacted, findings, uncertain_reason = _redact_string(text, policy)
    if high_risk:
        uncertain_reason = uncertain_reason or _uncertain_high_risk_reason(text, redacted, policy)
    if high_risk and uncertain_reason:
        return _fail_closed_result(text, policy, uncertain_reason, uncertain_strategy)
    return RedactionResult(
        value=redacted,
        status="redacted" if findings else "no_sensitive_fields",
        findings=tuple(findings),
    )


def redact_payload(
    payload: Any,
    *,
    policy: RedactionPolicy = DEFAULT_REDACTION_POLICY,
    high_risk: bool = False,
    uncertain_strategy: UncertainPayloadStrategy = "reject",
) -> RedactionResult:
    """Redact mappings, sequences, and text while preserving non-sensitive context."""

    redacted, findings, uncertain_reasons = _redact_any(payload, policy)
    if high_risk:
        uncertain_reason = next(iter(uncertain_reasons), None) or _payload_uncertain_reason(
            payload, redacted, policy
        )
        if uncertain_reason:
            return _fail_closed_result(payload, policy, uncertain_reason, uncertain_strategy)
    return RedactionResult(
        value=redacted,
        status="redacted" if findings else "no_sensitive_fields",
        findings=tuple(findings),
    )


def _redact_any(
    value: Any,
    policy: RedactionPolicy,
    *,
    key_hint: str | None = None,
) -> tuple[Any, list[RedactionFinding], list[str]]:
    if isinstance(value, Mapping):
        output = {}
        findings: list[RedactionFinding] = []
        uncertain_reasons: list[str] = []
        for key, item in value.items():
            redacted_item, item_findings, item_uncertain = _redact_any(
                item,
                policy,
                key_hint=str(key),
            )
            output[key] = redacted_item
            findings.extend(item_findings)
            uncertain_reasons.extend(item_uncertain)
        return output, findings, uncertain_reasons
    if isinstance(value, list):
        return _redact_sequence(value, policy, key_hint=key_hint, sequence_type=list)
    if isinstance(value, tuple):
        return _redact_sequence(value, policy, key_hint=key_hint, sequence_type=tuple)
    if isinstance(value, str):
        if key_hint and _is_sensitive_key(key_hint):
            return _redact_sensitive_value_for_key(value, key_hint, policy)
        redacted, findings, uncertain_reason = _redact_string(value, policy)
        return redacted, findings, [uncertain_reason] if uncertain_reason else []
    return value, [], []


def _redact_sequence(
    values: Sequence[Any],
    policy: RedactionPolicy,
    *,
    key_hint: str | None,
    sequence_type: type[list] | type[tuple],
) -> tuple[Any, list[RedactionFinding], list[str]]:
    output = []
    findings: list[RedactionFinding] = []
    uncertain_reasons: list[str] = []
    for item in values:
        redacted_item, item_findings, item_uncertain = _redact_any(
            item,
            policy,
            key_hint=key_hint,
        )
        output.append(redacted_item)
        findings.extend(item_findings)
        uncertain_reasons.extend(item_uncertain)
    return sequence_type(output), findings, uncertain_reasons


def _redact_sensitive_value_for_key(
    value: str,
    key: str,
    policy: RedactionPolicy,
) -> tuple[str, list[RedactionFinding], list[str]]:
    secret_type = _secret_type_from_key(key)
    if _CONNECTION_STRING_KEY_PATTERN.search(key):
        redacted, findings, uncertain_reason = _redact_string(value, policy)
        if findings:
            return redacted, findings, [uncertain_reason] if uncertain_reason else []
    finding = _finding(secret_type, value, "sensitive_key", policy)
    return finding.marker, [finding], []


def _redact_string(
    value: str,
    policy: RedactionPolicy,
) -> tuple[str, list[RedactionFinding], str | None]:
    findings: list[RedactionFinding] = []
    text = value

    for configured_value in policy.configured_secret_values:
        if configured_value:
            text = _replace_literal(
                text,
                configured_value,
                "configured_secret",
                "configured_value",
                policy,
                findings,
            )

    for pattern in policy.configured_secret_patterns:
        text = _replace_regex_group_or_full(
            text,
            pattern,
            "configured_secret",
            "configured_pattern",
            policy,
            findings,
        )

    text = _replace_regex_full(
        text,
        _PRIVATE_KEY_BLOCK_PATTERN,
        "private_key",
        "private_key_block",
        policy,
        findings,
    )
    text = _replace_credential_urls(text, policy, findings)
    text = _replace_regex_named_group(
        text,
        _AUTHORIZATION_BEARER_PATTERN,
        "token",
        "authorization_bearer",
        policy,
        findings,
        group_name="token",
    )
    text = _replace_regex_named_group(
        text,
        _BARE_BEARER_PATTERN,
        "token",
        "bearer_token",
        policy,
        findings,
        group_name="token",
    )
    text = _replace_regex_named_group(
        text,
        _COOKIE_HEADER_PATTERN,
        "cookie",
        "cookie_header",
        policy,
        findings,
        group_name="cookie",
    )
    text = _replace_regex_named_group(
        text,
        _SECRET_ASSIGNMENT_PATTERN,
        "secret",
        "named_assignment",
        policy,
        findings,
        group_name="value",
    )
    text = _replace_regex_named_group(
        text,
        _ENV_SECRET_ASSIGNMENT_PATTERN,
        "secret",
        "env_assignment",
        policy,
        findings,
        group_name="value",
    )
    text = _replace_query_secrets(text, policy, findings)
    for secret_type, pattern in _PROVIDER_KEY_PATTERNS:
        text = _replace_regex_full(text, pattern, secret_type, "provider_key", policy, findings)
    text = _replace_regex_full(
        text,
        _SESSION_ID_PATTERN,
        "session_id",
        "session_id",
        policy,
        findings,
    )

    uncertain_reason = None
    if _PRIVATE_KEY_BEGIN_PATTERN.search(text) and not _PRIVATE_KEY_BLOCK_PATTERN.search(value):
        uncertain_reason = "incomplete_private_key_material"
    return text, findings, uncertain_reason


def _replace_literal(
    text: str,
    literal: str,
    secret_type: str,
    detector: str,
    policy: RedactionPolicy,
    findings: list[RedactionFinding],
) -> str:
    if literal not in text:
        return text
    finding = _finding(secret_type, literal, detector, policy)
    findings.append(finding)
    return text.replace(literal, finding.marker)


def _replace_regex_full(
    text: str,
    pattern: re.Pattern[str],
    secret_type: str,
    detector: str,
    policy: RedactionPolicy,
    findings: list[RedactionFinding],
) -> str:
    def replace(match: re.Match[str]) -> str:
        finding = _finding(secret_type, match.group(0), detector, policy)
        findings.append(finding)
        return finding.marker

    return pattern.sub(replace, text)


def _replace_regex_group_or_full(
    text: str,
    pattern: re.Pattern[str],
    secret_type: str,
    detector: str,
    policy: RedactionPolicy,
    findings: list[RedactionFinding],
) -> str:
    group_name = "secret" if "secret" in pattern.groupindex else None
    if group_name:
        return _replace_regex_named_group(
            text,
            pattern,
            secret_type,
            detector,
            policy,
            findings,
            group_name=group_name,
        )
    return _replace_regex_full(text, pattern, secret_type, detector, policy, findings)


def _replace_regex_named_group(
    text: str,
    pattern: re.Pattern[str],
    secret_type: str,
    detector: str,
    policy: RedactionPolicy,
    findings: list[RedactionFinding],
    *,
    group_name: str,
) -> str:
    output = []
    cursor = 0
    for match in pattern.finditer(text):
        secret = match.group(group_name)
        finding = _finding(secret_type, secret, detector, policy)
        findings.append(finding)
        start, end = match.span(group_name)
        output.append(text[cursor:start])
        output.append(finding.marker)
        cursor = end
    if not output:
        return text
    output.append(text[cursor:])
    return "".join(output)


def _replace_credential_urls(
    text: str,
    policy: RedactionPolicy,
    findings: list[RedactionFinding],
) -> str:
    output = []
    cursor = 0
    for match in _CREDENTIAL_URL_PATTERN.finditer(text):
        password = match.group("password")
        finding = _finding("database_credential", password, "credentialed_url", policy)
        findings.append(finding)
        start, end = match.span("password")
        output.append(text[cursor:start])
        output.append(finding.marker)
        cursor = end
    if not output:
        return text
    output.append(text[cursor:])
    return "".join(output)


def _replace_query_secrets(
    text: str,
    policy: RedactionPolicy,
    findings: list[RedactionFinding],
) -> str:
    output = []
    cursor = 0
    for match in _QUERY_SECRET_PATTERN.finditer(text):
        secret = match.group("value")
        secret_type = _secret_type_from_key(match.group("prefix"))
        finding = _finding(secret_type, secret, "query_secret", policy)
        findings.append(finding)
        start, end = match.span("value")
        output.append(text[cursor:start])
        output.append(finding.marker)
        cursor = end
    if not output:
        return text
    output.append(text[cursor:])
    return "".join(output)


def _finding(
    secret_type: str,
    value: str,
    detector: str,
    policy: RedactionPolicy,
) -> RedactionFinding:
    ref = stable_secret_ref(value, secret_type=secret_type, policy=policy)
    return RedactionFinding(
        secret_type=secret_type,
        marker=f"[REDACTED_{secret_type.upper()}:{ref}]",
        ref=ref,
        detector=detector,
    )


def _is_sensitive_key(key: str) -> bool:
    normalized = key.strip().lower()
    if normalized in _SAFE_REF_KEYS or _PUBLIC_KEY_PATTERN.search(normalized):
        return False
    return bool(_SENSITIVE_KEY_PATTERN.search(normalized))


def _secret_type_from_key(key: str) -> str:
    normalized = key.lower()
    if "cookie" in normalized:
        return "cookie"
    if "csrf" in normalized:
        return "csrf_token"
    if "session_id" in normalized:
        return "session_id"
    if "session" in normalized:
        return "session"
    if "refresh" in normalized:
        return "refresh_token"
    if "reset" in normalized:
        return "reset_token"
    if "api" in normalized or "access_key" in normalized:
        return "api_key"
    if "webhook" in normalized:
        return "webhook_secret"
    if "connector" in normalized:
        return "connector_secret"
    if "private_key" in normalized:
        return "private_key"
    if "password" in normalized or "credential" in normalized:
        return "credential"
    return "secret"


def _uncertain_high_risk_reason(
    original: str,
    redacted: str,
    policy: RedactionPolicy,
) -> str | None:
    if len(original) > policy.max_string_length:
        return "oversized_high_risk_payload"
    if _PRIVATE_KEY_BEGIN_PATTERN.search(original) and _PRIVATE_KEY_BEGIN_PATTERN.search(redacted):
        return "incomplete_private_key_material"
    env_lines = [
        line
        for line in original.splitlines()
        if re.match(r"\s*[A-Za-z_][A-Za-z0-9_]*\s*=", line)
    ]
    if len(env_lines) >= 6 and _GENERIC_SECRET_KEYWORD_PATTERN.search(original):
        return "uncertain_env_like_payload"
    return None


def _payload_uncertain_reason(
    payload: Any,
    redacted: Any,
    policy: RedactionPolicy,
) -> str | None:
    if isinstance(payload, str):
        return _uncertain_high_risk_reason(payload, str(redacted), policy)
    return None


def _fail_closed_result(
    payload: Any,
    policy: RedactionPolicy,
    reason: str,
    strategy: UncertainPayloadStrategy,
) -> RedactionResult:
    ref = stable_secret_ref(_shape_for_ref(payload), secret_type="payload", policy=policy)
    if strategy == "truncate":
        return RedactionResult(
            value=f"{policy.truncated_marker}:{ref}",
            status="truncated",
            action="truncate",
            reason=reason,
        )
    if strategy != "reject":
        raise ValueError("uncertain_strategy must be 'reject' or 'truncate'")
    return RedactionResult(value=None, status="rejected", action="reject", reason=reason)


def _shape_for_ref(payload: Any) -> str:
    if isinstance(payload, Mapping):
        keys = ",".join(sorted(str(key) for key in payload.keys()))
        return f"mapping:{keys}:{len(payload)}"
    if isinstance(payload, Sequence) and not isinstance(payload, str):
        return f"sequence:{type(payload).__name__}:{len(payload)}"
    if isinstance(payload, str):
        return f"str:{len(payload)}:{hashlib.sha256(payload.encode('utf-8')).hexdigest()}"
    return f"{type(payload).__name__}:{repr(payload)[:80]}"
