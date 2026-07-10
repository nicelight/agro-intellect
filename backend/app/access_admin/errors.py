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
    FARM_NOT_INITIALIZED = "FARM_NOT_INITIALIZED"
    FARM_STATE_CONFLICT = "FARM_STATE_CONFLICT"
    FARM_PERSISTENCE_FAILED = "FARM_PERSISTENCE_FAILED"
    PLANT_KEY_INVALID = "PLANT_KEY_INVALID"
    PLANT_KEY_CONFLICT = "PLANT_KEY_CONFLICT"
    PLANT_GRANT_TARGET_INVALID = "PLANT_GRANT_TARGET_INVALID"
    PLANT_GRANT_APPROVAL_FORBIDDEN = "PLANT_GRANT_APPROVAL_FORBIDDEN"
    PLANT_GRANT_NOT_FOUND = "PLANT_GRANT_NOT_FOUND"
    PLANT_STATE_CONFLICT = "PLANT_STATE_CONFLICT"
    PLANT_PERSISTENCE_FAILED = "PLANT_PERSISTENCE_FAILED"
    ADMIN_ACCOUNT_NOT_FOUND = "ADMIN_ACCOUNT_NOT_FOUND"
    ADMIN_MEMBERSHIP_NOT_FOUND = "ADMIN_MEMBERSHIP_NOT_FOUND"
    ADMIN_ACCOUNT_CONFLICT = "ADMIN_ACCOUNT_CONFLICT"
    ADMIN_LAST_BOSS_CONFLICT = "ADMIN_LAST_BOSS_CONFLICT"
    ADMIN_AUDIT_CURSOR_INVALID = "ADMIN_AUDIT_CURSOR_INVALID"
    ADMIN_PERSISTENCE_FAILED = "ADMIN_PERSISTENCE_FAILED"
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
    AuthErrorCode.FARM_NOT_INITIALIZED: ErrorDefinition(
        409,
        "Farm is not initialized. Run the local Farm bootstrap.",
    ),
    AuthErrorCode.FARM_STATE_CONFLICT: ErrorDefinition(
        409,
        "Farm state requires manual repair.",
    ),
    AuthErrorCode.FARM_PERSISTENCE_FAILED: ErrorDefinition(
        500,
        "Farm request could not be completed.",
    ),
    AuthErrorCode.PLANT_KEY_INVALID: ErrorDefinition(
        422,
        "Plant key is invalid.",
    ),
    AuthErrorCode.PLANT_KEY_CONFLICT: ErrorDefinition(
        409,
        "Plant key is already in use.",
    ),
    AuthErrorCode.PLANT_GRANT_TARGET_INVALID: ErrorDefinition(
        422,
        "Plant access target is invalid.",
    ),
    AuthErrorCode.PLANT_GRANT_APPROVAL_FORBIDDEN: ErrorDefinition(
        422,
        "Action approval cannot be granted to this membership.",
    ),
    AuthErrorCode.PLANT_GRANT_NOT_FOUND: ErrorDefinition(
        404,
        "Plant access grant is not available.",
    ),
    AuthErrorCode.PLANT_STATE_CONFLICT: ErrorDefinition(
        409,
        "Plant state changed. Retry with current state.",
    ),
    AuthErrorCode.PLANT_PERSISTENCE_FAILED: ErrorDefinition(
        500,
        "Plant request could not be completed.",
    ),
    AuthErrorCode.ADMIN_ACCOUNT_NOT_FOUND: ErrorDefinition(
        404,
        "Admin account target is not available.",
    ),
    AuthErrorCode.ADMIN_MEMBERSHIP_NOT_FOUND: ErrorDefinition(
        404,
        "Admin membership target is not available.",
    ),
    AuthErrorCode.ADMIN_ACCOUNT_CONFLICT: ErrorDefinition(
        409,
        "Account login is already in use.",
    ),
    AuthErrorCode.ADMIN_LAST_BOSS_CONFLICT: ErrorDefinition(
        409,
        "At least one active Boss must remain.",
    ),
    AuthErrorCode.ADMIN_AUDIT_CURSOR_INVALID: ErrorDefinition(
        422,
        "Audit cursor is invalid.",
    ),
    AuthErrorCode.ADMIN_PERSISTENCE_FAILED: ErrorDefinition(
        500,
        "Admin request could not be completed.",
    ),
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
