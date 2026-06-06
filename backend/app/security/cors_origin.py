"""CORS/origin validation — fail-closed by default."""

from __future__ import annotations


def validate_cors_origin(
    origin: str | None,
    allowed_origins: tuple[str, ...],
) -> bool:
    if not allowed_origins:
        return False
    if origin is None:
        return False
    return origin in allowed_origins


def validate_cors_config(allowed_origins: tuple[str, ...]) -> None:
    from backend.app.api.errors import AppError, ErrorCode

    if not allowed_origins:
        raise AppError(
            code=ErrorCode.INVALID_CONFIG,
            message="CORS allowed_origins must not be empty. "
            "Explicitly list origins or use loopback mode.",
            next_actions=["configure_allowed_origins", "use_loopback"],
        )
    for origin in allowed_origins:
        if origin == "*":
            raise AppError(
                code=ErrorCode.INVALID_CONFIG,
                message="Wildcard CORS origin '*' is too broad for MVP. "
                "List explicit origins.",
                next_actions=["configure_explicit_origins"],
            )
