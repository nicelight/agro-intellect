"""Storage prompt guard — ensures local storage text does not imply upload or server sync."""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class StoragePromptValidation:
    verdict: str  # "pass" or "fail"
    reason: str | None = None
    matched_patterns: tuple[str, ...] = ()


_UPLOAD_IMPLICATION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r'\bupload\b', re.IGNORECASE),
    re.compile(r'\bbackup\b', re.IGNORECASE),
    re.compile(r'\bcloud\b', re.IGNORECASE),
    re.compile(r'\bserver\b', re.IGNORECASE),
    re.compile(r'\bsynchroniz(s?e|ing|ation)\b', re.IGNORECASE),
    re.compile(r'\bremote\b', re.IGNORECASE),
    re.compile(r'\bhosted\b', re.IGNORECASE),
    re.compile(r'\bonline\b', re.IGNORECASE),
)


def validate_storage_prompt(text: str) -> StoragePromptValidation:
    matched = [p.pattern for p in _UPLOAD_IMPLICATION_PATTERNS if p.search(text)]
    if matched:
        return StoragePromptValidation(
            verdict="fail",
            reason=f"Storage prompt contains upload/server-sync implications: {matched}",
            matched_patterns=tuple(matched),
        )
    return StoragePromptValidation(verdict="pass")
