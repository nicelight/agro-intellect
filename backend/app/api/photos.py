from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from email import policy as email_policy
from email.parser import BytesParser
import uuid

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..access_admin.actor_context import ActorContext
from ..access_admin.dependencies import (
    AuthorizedPlantRequest,
    require_plant_permission,
)
from ..access_admin.errors import request_id_for
from ..access_admin.permissions import OperationKind
from ..photo_intake import (
    MAX_UPLOAD_BYTES,
    PHOTO_TYPES,
    PhotoArtifactStore,
    PhotoCatalogItem,
    PhotoIntakeError,
    PhotoIntakeErrorCode,
    PhotoIntakeService,
    PhotoUploadInput,
)
from ..timeline import TimelineJsonlAppender


router = APIRouter(prefix="/api", tags=["photos"])


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str


class ErrorEnvelope(BaseModel):
    error: ErrorDetail


class PhotoCatalogSummary(BaseModel):
    photo_id: uuid.UUID
    farm_id: uuid.UUID
    plant_id: uuid.UUID
    photo_type: str
    captured_at: datetime
    uploaded_at: datetime
    content_type: str
    size_bytes: int
    sha256: str
    original_file_ref: str
    manifest_ref: str
    check_in_id: uuid.UUID | None
    source_refs: dict[str, object]
    event_refs: dict[str, object]
    local_only: bool
    can_train_on: bool


class PhotoCatalogList(BaseModel):
    items: list[PhotoCatalogSummary]
    next_cursor: str | None = None


@dataclass(frozen=True, slots=True)
class _PhotoErrorDefinition:
    status_code: int
    message: str


_ERROR_DEFINITIONS = {
    PhotoIntakeErrorCode.AUTH_PLANT_FORBIDDEN: _PhotoErrorDefinition(
        404,
        "Plant is not available.",
    ),
    PhotoIntakeErrorCode.PHOTO_NOT_FOUND: _PhotoErrorDefinition(
        404,
        "Photo is not available.",
    ),
    PhotoIntakeErrorCode.PHOTO_TYPE_INVALID: _PhotoErrorDefinition(
        422,
        "Photo type is invalid.",
    ),
    PhotoIntakeErrorCode.UPLOAD_FILE_REQUIRED: _PhotoErrorDefinition(
        422,
        "Upload file is required.",
    ),
    PhotoIntakeErrorCode.UPLOAD_TOO_LARGE: _PhotoErrorDefinition(
        413,
        "Upload is too large.",
    ),
    PhotoIntakeErrorCode.UNSUPPORTED_MEDIA_TYPE: _PhotoErrorDefinition(
        415,
        "Unsupported media type.",
    ),
    PhotoIntakeErrorCode.PHOTO_CHECKSUM_MISMATCH: _PhotoErrorDefinition(
        500,
        "Photo checksum could not be verified.",
    ),
    PhotoIntakeErrorCode.PHOTO_ARTIFACT_WRITE_FAILED: _PhotoErrorDefinition(
        500,
        "Photo artifact could not be stored.",
    ),
    PhotoIntakeErrorCode.TIMELINE_APPEND_FAILED: _PhotoErrorDefinition(
        500,
        "Photo audit trail could not be recorded.",
    ),
    PhotoIntakeErrorCode.PHOTO_PERSISTENCE_FAILED: _PhotoErrorDefinition(
        500,
        "Photo intake could not be completed.",
    ),
    PhotoIntakeErrorCode.VALIDATION_FAILED: _PhotoErrorDefinition(
        422,
        "Request validation failed.",
    ),
}

_ERROR_RESPONSES = {
    401: {"model": ErrorEnvelope},
    403: {"model": ErrorEnvelope},
    404: {"model": ErrorEnvelope},
    413: {"model": ErrorEnvelope},
    415: {"model": ErrorEnvelope},
    422: {"model": ErrorEnvelope},
    500: {"model": ErrorEnvelope},
}
_MULTIPART_BODY_LIMIT_BYTES = MAX_UPLOAD_BYTES + 1024 * 1024
_UPLOAD_REQUEST_BODY = {
    "required": True,
    "content": {
        "multipart/form-data": {
            "schema": {
                "type": "object",
                "required": ["file", "photo_type"],
                "properties": {
                    "file": {"type": "string", "format": "binary"},
                    "photo_type": {
                        "type": "string",
                        "enum": sorted(PHOTO_TYPES),
                    },
                    "captured_at": {
                        "type": "string",
                        "format": "date-time",
                        "nullable": True,
                    },
                    "check_in_id": {
                        "type": "string",
                        "format": "uuid",
                        "nullable": True,
                    },
                },
                "additionalProperties": False,
            }
        }
    },
}
_normal_read = require_plant_permission(OperationKind.NORMAL_READ)
_operate = require_plant_permission(OperationKind.OPERATE)


@dataclass(frozen=True, slots=True)
class _ParsedUpload:
    content: bytes
    content_type: str
    filename: str | None
    photo_type: str
    captured_at: datetime | None
    check_in_id: uuid.UUID | None


@router.post(
    "/plants/{plant_id}/photos",
    response_model=PhotoCatalogSummary,
    status_code=201,
    responses=_ERROR_RESPONSES,
    openapi_extra={"requestBody": _UPLOAD_REQUEST_BODY},
)
async def upload_photo(
    plant_id: uuid.UUID,
    response: Response,
    request: Request,
    authorized: AuthorizedPlantRequest = Depends(_operate),
) -> PhotoCatalogSummary | JSONResponse:
    try:
        parsed = await _parse_multipart_upload(request)
    except PhotoIntakeError as error:
        return _photo_error_response(request, error.code)

    result = _run_photo_command(
        request,
        authorized.actor,
        lambda service, actor: service.accept_photo(
            actor,
            plant_id=plant_id,
            upload=PhotoUploadInput(
                content=parsed.content,
                content_type=parsed.content_type,
                photo_type=parsed.photo_type,
                captured_at=parsed.captured_at,
                check_in_id=parsed.check_in_id,
                original_filename=parsed.filename,
            ),
        ),
    )
    if isinstance(result, JSONResponse):
        return result
    _no_store(response)
    return _photo_summary(result.item)


@router.get(
    "/plants/{plant_id}/photos",
    response_model=PhotoCatalogList,
    responses=_ERROR_RESPONSES,
)
def list_photos(
    plant_id: uuid.UUID,
    response: Response,
    request: Request,
    cursor: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    authorized: AuthorizedPlantRequest = Depends(_normal_read),
) -> PhotoCatalogList | JSONResponse:
    result = _run_photo_command(
        request,
        authorized.actor,
        lambda service, actor: service.list_photos(
            actor,
            plant_id=plant_id,
            cursor=cursor,
            limit=limit,
        ),
    )
    if isinstance(result, JSONResponse):
        return result
    _no_store(response)
    return PhotoCatalogList(
        items=[_photo_summary(item) for item in result.items],
        next_cursor=result.next_cursor,
    )


@router.get(
    "/plants/{plant_id}/photos/{photo_id}",
    response_model=PhotoCatalogSummary,
    responses=_ERROR_RESPONSES,
)
def get_photo(
    plant_id: uuid.UUID,
    photo_id: uuid.UUID,
    response: Response,
    request: Request,
    authorized: AuthorizedPlantRequest = Depends(_normal_read),
) -> PhotoCatalogSummary | JSONResponse:
    result = _run_photo_command(
        request,
        authorized.actor,
        lambda service, actor: service.get_photo(
            actor,
            plant_id=plant_id,
            photo_id=photo_id,
        ),
    )
    if isinstance(result, JSONResponse):
        return result
    _no_store(response)
    return _photo_summary(result)


async def _parse_multipart_upload(request: Request) -> _ParsedUpload:
    content_type = request.headers.get("content-type", "")
    if not content_type.lower().startswith("multipart/form-data"):
        raise PhotoIntakeError(PhotoIntakeErrorCode.VALIDATION_FAILED)
    try:
        content_length = int(request.headers.get("content-length", "0"))
    except ValueError:
        raise PhotoIntakeError(PhotoIntakeErrorCode.VALIDATION_FAILED) from None
    if content_length > _MULTIPART_BODY_LIMIT_BYTES:
        raise PhotoIntakeError(PhotoIntakeErrorCode.UPLOAD_TOO_LARGE)

    body = bytearray()
    try:
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > _MULTIPART_BODY_LIMIT_BYTES:
                raise PhotoIntakeError(PhotoIntakeErrorCode.UPLOAD_TOO_LARGE)
    except PhotoIntakeError:
        raise
    except Exception:
        raise PhotoIntakeError(PhotoIntakeErrorCode.PHOTO_PERSISTENCE_FAILED) from None

    try:
        message = BytesParser(policy=email_policy.default).parsebytes(
            b"Content-Type: "
            + content_type.encode("ascii", "ignore")
            + b"\r\nMIME-Version: 1.0\r\n\r\n"
            + bytes(body)
        )
    except Exception:
        raise PhotoIntakeError(PhotoIntakeErrorCode.VALIDATION_FAILED) from None
    if not message.is_multipart():
        raise PhotoIntakeError(PhotoIntakeErrorCode.VALIDATION_FAILED)

    fields: dict[str, str] = {}
    file_content: bytes | None = None
    file_content_type = ""
    filename: str | None = None
    allowed_fields = {"file", "photo_type", "captured_at", "check_in_id"}
    for part in message.iter_parts():
        if part.get_content_disposition() != "form-data":
            continue
        name = part.get_param("name", header="content-disposition")
        if not isinstance(name, str) or name not in allowed_fields:
            raise PhotoIntakeError(PhotoIntakeErrorCode.VALIDATION_FAILED)
        payload = part.get_payload(decode=True) or b""
        if name == "file":
            file_content = payload
            file_content_type = part.get_content_type()
            filename = part.get_filename()
            continue
        try:
            fields[name] = payload.decode("utf-8")
        except UnicodeDecodeError:
            raise PhotoIntakeError(PhotoIntakeErrorCode.VALIDATION_FAILED) from None

    if file_content is None:
        raise PhotoIntakeError(PhotoIntakeErrorCode.UPLOAD_FILE_REQUIRED)
    photo_type = fields.get("photo_type")
    if photo_type is None:
        raise PhotoIntakeError(PhotoIntakeErrorCode.VALIDATION_FAILED)
    return _ParsedUpload(
        content=file_content,
        content_type=file_content_type,
        filename=filename,
        photo_type=photo_type,
        captured_at=_optional_datetime(fields.get("captured_at")),
        check_in_id=_optional_uuid(fields.get("check_in_id")),
    )


def _run_photo_command(request: Request, actor: ActorContext, command):
    try:
        with request.app.state.database.session() as session:
            service = PhotoIntakeService(
                session,
                artifact_store=PhotoArtifactStore(request.app.state.settings),
                timeline_append=TimelineJsonlAppender(request.app.state.settings),
            )
            return command(service, actor)
    except PhotoIntakeError as error:
        return _photo_error_response(request, error.code)
    except Exception:
        return _photo_error_response(
            request,
            PhotoIntakeErrorCode.PHOTO_PERSISTENCE_FAILED,
        )


def _photo_error_response(
    request: Request,
    code: PhotoIntakeErrorCode,
) -> JSONResponse:
    definition = _ERROR_DEFINITIONS[code]
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


def _photo_summary(item: PhotoCatalogItem) -> PhotoCatalogSummary:
    return PhotoCatalogSummary(
        photo_id=item.photo_id,
        farm_id=item.farm_id,
        plant_id=item.plant_id,
        photo_type=item.photo_type,
        captured_at=_timestamp(item.captured_at),
        uploaded_at=_timestamp(item.uploaded_at),
        content_type=item.content_type,
        size_bytes=item.size_bytes,
        sha256=item.sha256,
        original_file_ref=item.original_file_ref,
        manifest_ref=item.manifest_ref,
        check_in_id=item.check_in_id,
        source_refs=dict(item.source_refs or {}),
        event_refs=dict(item.event_refs or {}),
        local_only=item.local_only,
        can_train_on=item.can_train_on,
    )


def _timestamp(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def _optional_datetime(value: str | None) -> datetime | None:
    if value is None or value == "":
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise PhotoIntakeError(PhotoIntakeErrorCode.VALIDATION_FAILED) from None


def _optional_uuid(value: str | None) -> uuid.UUID | None:
    if value is None or value == "":
        return None
    try:
        return uuid.UUID(value)
    except ValueError:
        raise PhotoIntakeError(PhotoIntakeErrorCode.VALIDATION_FAILED) from None


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


__all__ = ["router"]
