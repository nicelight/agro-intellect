from __future__ import annotations

from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError

from backend.app.core.security import (
    generate_session_token,
    hash_session_token,
    redact_auth_material,
    verify_session_token,
)


ARGON2_TIME_COST = 3
ARGON2_MEMORY_COST = 65536
ARGON2_PARALLELISM = 4
ARGON2_HASH_LENGTH = 32
ARGON2_SALT_LENGTH = 16

_PASSWORD_HASHER = PasswordHasher(
    time_cost=ARGON2_TIME_COST,
    memory_cost=ARGON2_MEMORY_COST,
    parallelism=ARGON2_PARALLELISM,
    hash_len=ARGON2_HASH_LENGTH,
    salt_len=ARGON2_SALT_LENGTH,
    type=Type.ID,
)


def hash_password(password: str) -> str:
    """Return an Argon2id PHC string for a local Account password."""

    if not isinstance(password, str):
        raise TypeError("Password must be a string.")
    return _PASSWORD_HASHER.hash(password)


def verify_password(password: object, password_hash: object) -> bool:
    """Fail closed for a mismatch or malformed Argon2 password hash."""

    if not isinstance(password, str) or not isinstance(password_hash, str):
        return False
    try:
        return _PASSWORD_HASHER.verify(password_hash, password)
    except (InvalidHashError, VerificationError):
        return False


__all__ = [
    "ARGON2_HASH_LENGTH",
    "ARGON2_MEMORY_COST",
    "ARGON2_PARALLELISM",
    "ARGON2_SALT_LENGTH",
    "ARGON2_TIME_COST",
    "generate_session_token",
    "hash_password",
    "hash_session_token",
    "redact_auth_material",
    "verify_password",
    "verify_session_token",
]
