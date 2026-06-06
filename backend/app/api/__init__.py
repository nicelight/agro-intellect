"""FastAPI application and shared API utilities."""

from backend.app.api.app import create_app
from backend.app.api.csrf import CsrfProtection
from backend.app.api.errors import AppError, ErrorCode, error_response
from backend.app.api.schemas import (
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    MeResponse,
)

__all__ = [
    "AppError",
    "CsrfProtection",
    "ErrorCode",
    "LoginRequest",
    "LoginResponse",
    "LogoutResponse",
    "MeResponse",
    "create_app",
    "error_response",
]
