import logging
import time
from uuid import uuid4

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.logging import log_request
from app.core.request_context import reset_request_context, set_request_context


logger = logging.getLogger("app.request")

HEALTH_LOG_EXCLUDED_PREFIXES = (
    "/api/v1/health/",
)


def get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


def build_error_body(*, request_id: str, code: str, message: str, details=None) -> dict:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details,
            "request_id": request_id,
        }
    }


async def request_id_middleware(request: Request, call_next):
    started_at = time.perf_counter()
    request.state.request_id = str(uuid4())
    request_path = request.url.path
    request_context_tokens = set_request_context(
        request_id=request.state.request_id,
        client_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        if not any(request_path.startswith(prefix) for prefix in HEALTH_LOG_EXCLUDED_PREFIXES):
            log_request(
                logger,
                method=request.method,
                path=request_path,
                status_code=response.status_code,
                started_at=started_at,
                user_id=getattr(request.state, "user_id", None),
            )
        return response
    except Exception:
        logger.exception(
            "request.failed",
            extra={
                "event_type": "request.failed",
                "method": request.method,
                "path": request_path,
            },
        )
        raise
    finally:
        reset_request_context(request_context_tokens)


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    logger.warning(
        "http_exception",
        extra={
            "event_type": "http_exception",
            "method": request.method,
            "path": request.url.path,
            "status_code": exc.status_code,
            "user_id": getattr(request.state, "user_id", None),
            "error_code": "http_error",
        },
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=build_error_body(
            request_id=get_request_id(request),
            code="http_error",
            message=str(exc.detail),
        ),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    logger.warning(
        "validation_exception",
        extra={
            "event_type": "validation_exception",
            "method": request.method,
            "path": request.url.path,
            "status_code": 422,
            "user_id": getattr(request.state, "user_id", None),
            "error_code": "validation_error",
        },
    )
    return JSONResponse(
        status_code=422,
        content=build_error_body(
            request_id=get_request_id(request),
            code="validation_error",
            message="Ошибка валидации запроса",
            details=exc.errors(),
        ),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "unhandled_exception",
        extra={
            "event_type": "unhandled_exception",
            "method": request.method,
            "path": request.url.path,
            "status_code": 500,
            "user_id": getattr(request.state, "user_id", None),
            "error_code": "internal_error",
        },
    )
    return JSONResponse(
        status_code=500,
        content=build_error_body(
            request_id=get_request_id(request),
            code="internal_error",
            message="Внутренняя ошибка сервера",
        ),
    )