from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from backend.app.api.csrf import CsrfProtection
from backend.app.api.errors import AppError, error_response
from backend.app.api.routes.auth import router as auth_router
from backend.app.api.routes.farm import router as farm_router
from backend.app.api.routes.plants import router as plants_router
from backend.app.config.deployment import DeploymentConfig, DeploymentMode
from backend.app.db.engine import dispose_engine
from backend.app.security.cors_origin import validate_cors_config


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield
    await dispose_engine()


def create_app(config: DeploymentConfig | None = None) -> FastAPI:
    cfg = config or DeploymentConfig()

    if cfg.mode == DeploymentMode.LAN:
        validate_cors_config(cfg.allowed_origins)

    app = FastAPI(title="Agro Intellect API", version="0.1.0", lifespan=lifespan)

    if cfg.mode == DeploymentMode.LAN:
        from fastapi.middleware.cors import CORSMiddleware

        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(cfg.allowed_origins),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    if cfg.csrf_protection_enabled:
        _add_csrf_protection(app, cfg)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.exception_handler(AppError)
    def handle_app_error(_request: Request, exc: AppError):
        return JSONResponse(
            status_code=_http_status(exc),
            content=error_response(exc),
        )

    app.include_router(auth_router)
    app.include_router(farm_router)
    app.include_router(plants_router)

    return app


def _add_csrf_protection(app: FastAPI, cfg: DeploymentConfig) -> None:
    from backend.app.api.errors import ErrorCode

    csrf = CsrfProtection()

    @app.middleware("http")
    async def csrf_middleware(request: Request, call_next):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return await call_next(request)

        token = request.headers.get(csrf.get_csrf_header())
        if not csrf.validate_token(token, csrf.token):
            return JSONResponse(
                status_code=403,
                content=error_response(
                    AppError(
                        code=ErrorCode.PERMISSION_DENIED,
                        message="CSRF token is missing or invalid.",
                        next_actions=["include_valid_csrf_token"],
                    )
                ),
            )
        return await call_next(request)

    app.state._csrf_protection = csrf


def _http_status(error: AppError) -> int:
    from backend.app.api.errors import ErrorCode

    mapping = {
        ErrorCode.INVALID_REQUEST: 400,
        ErrorCode.INVALID_SESSION: 401,
        ErrorCode.INVALID_CONFIG: 422,
        ErrorCode.PERMISSION_DENIED: 403,
        ErrorCode.NOT_FOUND: 404,
        ErrorCode.CONFLICT: 409,
        ErrorCode.ARCHIVED_RESOURCE: 410,
        ErrorCode.VALIDATION_FAILED: 422,
        ErrorCode.UPLOAD_REJECTED: 422,
        ErrorCode.APPROVAL_REQUIRED: 403,
        ErrorCode.SAFETY_GATE_BLOCKED: 403,
        ErrorCode.STALE_OR_MISSING_EVIDENCE: 422,
        ErrorCode.RATE_LIMITED: 429,
        ErrorCode.PROVIDER_UNAVAILABLE: 503,
        ErrorCode.INTERNAL_ERROR: 500,
    }
    return mapping.get(error.code, 500)
