from __future__ import annotations

import hashlib

from argon2 import Type, extract_parameters

from backend.app.access_admin import security as security_module
from backend.app.access_admin.security import (
    ARGON2_HASH_LENGTH,
    ARGON2_MEMORY_COST,
    ARGON2_PARALLELISM,
    ARGON2_SALT_LENGTH,
    ARGON2_TIME_COST,
    generate_session_token,
    hash_password,
    hash_session_token,
    redact_auth_material,
    verify_password,
    verify_password_for_account,
    verify_session_token,
)
from backend.app.core import security as core_security


_TEST_TOKEN = "A" * core_security.SESSION_TOKEN_MIN_LENGTH
_OTHER_TEST_TOKEN = "B" * core_security.SESSION_TOKEN_MIN_LENGTH


def test_password_hash_uses_exact_argon2id_contract_and_random_salt():
    password = "test-only-password"

    password_hash = hash_password(password)
    second_hash = hash_password(password)
    parameters = extract_parameters(password_hash)

    assert password_hash.startswith("$argon2id$")
    assert password not in password_hash
    assert password_hash != second_hash
    assert parameters.type is Type.ID
    assert parameters.time_cost == ARGON2_TIME_COST == 3
    assert parameters.memory_cost == ARGON2_MEMORY_COST == 65536
    assert parameters.parallelism == ARGON2_PARALLELISM == 4
    assert parameters.hash_len == ARGON2_HASH_LENGTH == 32
    assert parameters.salt_len == ARGON2_SALT_LENGTH == 16


def test_password_verification_fails_closed_for_mismatch_and_malformed_hash():
    password_hash = hash_password("test-only-password")

    assert verify_password("test-only-password", password_hash) is True
    assert verify_password("wrong-test-password", password_hash) is False
    assert verify_password("test-only-password", "not-a-phc-hash") is False
    assert verify_password(None, password_hash) is False
    assert verify_password("test-only-password", None) is False


def test_account_password_verification_uses_real_or_dummy_hash_once(monkeypatch):
    observed_hashes: list[object] = []
    real_hash = "synthetic-real-phc"

    def tracked_verify(password: object, password_hash: object) -> bool:
        observed_hashes.append(password_hash)
        return password == "correct-password" and password_hash == real_hash

    monkeypatch.setattr(security_module, "verify_password", tracked_verify)

    assert verify_password_for_account("wrong-password", None) is False
    assert verify_password_for_account("wrong-password", real_hash) is False
    assert verify_password_for_account("correct-password", real_hash) is True

    assert len(observed_hashes) == 3
    assert isinstance(observed_hashes[0], str)
    assert observed_hashes[0] != real_hash
    assert observed_hashes[1:] == [real_hash, real_hash]
    dummy_parameters = extract_parameters(observed_hashes[0])
    assert dummy_parameters.type is Type.ID
    assert dummy_parameters.time_cost == ARGON2_TIME_COST
    assert dummy_parameters.memory_cost == ARGON2_MEMORY_COST
    assert dummy_parameters.parallelism == ARGON2_PARALLELISM
    assert dummy_parameters.hash_len == ARGON2_HASH_LENGTH
    assert dummy_parameters.salt_len == ARGON2_SALT_LENGTH


def test_session_token_generation_uses_32_random_bytes(monkeypatch):
    requested_sizes: list[int] = []

    def fake_token_urlsafe(size: int) -> str:
        requested_sizes.append(size)
        return _TEST_TOKEN

    monkeypatch.setattr(core_security.secrets, "token_urlsafe", fake_token_urlsafe)

    assert generate_session_token() == _TEST_TOKEN
    assert requested_sizes == [core_security.SESSION_TOKEN_BYTES]
    assert core_security.SESSION_TOKEN_BYTES == 32


def test_generated_session_token_has_canonical_url_safe_shape():
    generated_token = generate_session_token()

    assert core_security.is_valid_session_token(generated_token)
    assert len(generated_token) >= core_security.SESSION_TOKEN_MIN_LENGTH


def test_session_token_hash_is_lowercase_sha256_and_raw_token_is_not_returned():
    token_hash = hash_session_token(_TEST_TOKEN)

    assert token_hash == hashlib.sha256(_TEST_TOKEN.encode("utf-8")).hexdigest()
    assert token_hash != _TEST_TOKEN
    assert len(token_hash) == core_security.SESSION_TOKEN_HASH_LENGTH == 64
    assert core_security.is_valid_session_token_hash(token_hash)


def test_session_token_verification_uses_constant_time_digest_comparison(monkeypatch):
    comparison_shapes: list[tuple[int, int]] = []

    def fake_compare_digest(first: str, second: str) -> bool:
        comparison_shapes.append((len(first), len(second)))
        return first == second

    monkeypatch.setattr(core_security.hmac, "compare_digest", fake_compare_digest)

    token_hash = hash_session_token(_TEST_TOKEN)
    assert verify_session_token(_TEST_TOKEN, token_hash) is True
    assert comparison_shapes == [(64, 64)]


def test_session_token_verification_rejects_wrong_and_malformed_values():
    token_hash = hash_session_token(_TEST_TOKEN)

    assert verify_session_token(_OTHER_TEST_TOKEN, token_hash) is False
    assert verify_session_token("", token_hash) is False
    assert verify_session_token("too-short", token_hash) is False
    assert verify_session_token(_TEST_TOKEN, "A" * 64) is False
    assert verify_session_token(_TEST_TOKEN, "not-a-sha256-digest") is False


def test_auth_redaction_covers_password_token_hash_cookie_and_auth_headers():
    raw_password = "synthetic-password-value"
    raw_token = "synthetic-token-value"
    token_hash = "c" * 64
    error_text = (
        f"password={raw_password} token={raw_token} token_hash={token_hash} "
        f"Cookie: agro_intellect_session={raw_token}\n"
        f"Authorization: Bearer {raw_token}"
    )

    redacted = redact_auth_material(
        error_text,
        secret_values=(raw_password, raw_token, token_hash),
    )

    assert raw_password not in redacted
    assert raw_token not in redacted
    assert token_hash not in redacted
    assert "password=***" in redacted
    assert "token=***" in redacted
    assert "token_hash=***" in redacted
    assert "Cookie: ***" in redacted
    assert "Authorization: ***" in redacted


def test_auth_redaction_masks_session_cookie_assignment_without_secret_hint():
    redacted = redact_auth_material(
        "agro_intellect_session=synthetic-cookie-value"
    )

    assert redacted == "agro_intellect_session=***"
