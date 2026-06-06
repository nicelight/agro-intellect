"""Simple CSRF-equivalent write protection for loopback/LAN."""

from __future__ import annotations

import secrets
from hmac import compare_digest


class CsrfProtection:
    def __init__(self, token: str | None = None) -> None:
        self._token = token or secrets.token_urlsafe(32)

    @property
    def token(self) -> str:
        return self._token

    def generate_token(self) -> str:
        self._token = secrets.token_urlsafe(32)
        return self._token

    def validate_token(self, token: str | None, expected: str) -> bool:
        if token is None:
            return False
        if not token or not expected:
            return False
        return compare_digest(token, expected)

    @staticmethod
    def get_csrf_header() -> str:
        return "X-CSRF-Token"
