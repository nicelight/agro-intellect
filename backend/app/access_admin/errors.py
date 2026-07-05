from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import re
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


class AuthErrorCode(StrEnum):
    SESSION_REQUIRED = "AUTH_SESSION_REQUIRED"
    SESSION_INVALID = "AUTH_SESSION_INVALID"
    SESSION_EXPIRED = "AUTH_SESSION_EXPIRED"
    CREDENTIAL_INVALID = "AUTH_CREDENTIAL_INVALID"
    ACCOUNT_DISABLED = "AUTH_ACCOUNT_DISABLED"
    MEMBERSHIP_REQUIRED = "AUTH_MEMBERSHIP_REQUIRED"
    MEMBERSHIP_DISABLED = "AUTH_MEMBERSHIP_DISABLED"
    FORBIDDEN = "AUTH_FORBIDDEN"
    PLANT_FORBIDDEN = "AUTH_PLANT_FORBIDDEN"
    VALIDATION_FAILED = "VALIDATION_FAILED"


@dataclass(frozen=True, slots=True)
class ErrorDefinition:
    status_code: int
    message: str


ERROR_DEFINITIONS = {
    AuthErrorCode.SESSION_REQUIRED: ErrorDefinition(401, "Authentication required."),
    AuthErrorCode.SESSION_INVALID: ErrorDefinition(401, "Session is invalid."),
    AuthErrorCode.SESSION_EXPIRED: ErrorDefinition(401, "Session has expired."),
    AuthErrorCode.CREDENTIAL_INVALID: ErrorDefinition(
        401,
        "Invalid login or password.",
    ),
    AuthErrorCode.ACCOUNT_DISABLED: ErrorDefinition(403, "Account is disabled."),
    AuthErrorCode.MEMBERSHIP_REQUIRED: ErrorDefinition(
        403,
        "Farm membership is required.",
    ),
    AuthErrorCode.MEMBERSHIP_DISABLED: ErrorDefinition(
        403,
        "Farm membership is disabled.",
    ),
    AuthErrorCode.FORBIDDEN: ErrorDefinition(403, "Request is not allowed."),
    AuthErrorCode.PLANT_FORBIDDEN: ErrorDefinition(404, "Plant is not available."),
    AuthErrorCode.VALIDATION_FAILED: ErrorDefinition(
        422,
        "Request validation failed.",
    ),
}


def request_id_for(request: Request) -> str:
    existing = getattr(request.state, "request_id", None)
    if isinstance(existing, str):
        return existing

    supplied = request.headers.get("x-request-id", "").strip()
    request_id = (
        supplied
        if _REQUEST_ID_PATTERN.fullmatch(supplied)
        else f"req_{uuid.uuid4().hex}"
    )
    request.state.request_id = request_id
    return request_id


def auth_error_response(
    request: Request,
    code: AuthErrorCode,
) -> JSONResponse:
    definition = ERROR_DEFINITIONS[code]
    return JSONResponse(
        status_code=definition.status_code,
        content={
            "error": {
                "code": code.value,
                "message": definition.message,
                "request_id": request_id_for(request),
            }
        },
        headers={"Cache-Control": "no-store"},
    )


async def validation_error_handler(
    request: Request,
    _error: RequestValidationError,
) -> JSONResponse:
    return auth_error_response(request, AuthErrorCode.VALIDATION_FAILED)


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, validation_error_handler)


__all__ = [
    "AuthErrorCode",
    "auth_error_response",
    "install_error_handlers",
    "request_id_for",
]
