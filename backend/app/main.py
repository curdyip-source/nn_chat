import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.auth import router as auth_router
from app.api.routes.audit import router as audit_router
from app.api.routes.cdek import router as cdek_router
from app.api.routes.contacts import router as contacts_router
from app.api.routes.documents import router as documents_router
from app.api.routes.inventories import router as inventories_router
from app.api.routes.message_attachments import router as message_attachments_router
from app.api.routes.media import router as media_router
from app.api.routes.messages import router as messages_router
from app.api.routes.orders import router as orders_router
from app.api.routes.product_registrations import router as product_registrations_router
from app.api.routes.products import router as products_router
from app.api.routes.reference_data import router as reference_data_router
from app.api.routes.system import router as system_router
from app.api.routes.user_devices import router as user_devices_router
from app.api.routes.users import router as users_router
from app.core.config import CORS_ALLOW_CREDENTIALS, CORS_ALLOW_HEADERS, CORS_ALLOW_METHODS, CORS_ALLOW_ORIGINS, validate_runtime_config
from app.core.errors import http_exception_handler, request_id_middleware, unhandled_exception_handler, validation_exception_handler
from app.core.idempotency import idempotency_middleware
from app.core.logging import configure_logging, init_error_tracking


configure_logging()
logger = logging.getLogger("app.startup")


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Capture the running loop so threadpool request handlers can publish SSE events onto it.
    from app.services.message_stream import broker

    broker.bind_loop(asyncio.get_running_loop())
    yield


def create_app() -> FastAPI:
    validate_runtime_config()
    init_error_tracking()
    application = FastAPI(lifespan=lifespan)
    # Registered before request_id_middleware so request_id stays the OUTERMOST middleware:
    # Starlette runs the last-registered middleware first, so idempotency runs inside request_id
    # (every request — including a replayed one — still gets a request id and access log).
    application.middleware("http")(idempotency_middleware)
    application.middleware("http")(request_id_middleware)
    application.add_exception_handler(HTTPException, http_exception_handler)
    application.add_exception_handler(RequestValidationError, validation_exception_handler)
    application.add_exception_handler(Exception, unhandled_exception_handler)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ALLOW_ORIGINS,
        allow_credentials=CORS_ALLOW_CREDENTIALS,
        allow_methods=CORS_ALLOW_METHODS,
        allow_headers=CORS_ALLOW_HEADERS,
    )

    @application.get("/")
    def read_root() -> dict:
        return {"message": "Backend works"}

    api_v1_router = APIRouter(prefix="/api/v1")
    api_v1_router.include_router(system_router)
    api_v1_router.include_router(auth_router)
    api_v1_router.include_router(audit_router)
    api_v1_router.include_router(cdek_router)
    api_v1_router.include_router(contacts_router)
    api_v1_router.include_router(documents_router)
    api_v1_router.include_router(reference_data_router)
    api_v1_router.include_router(products_router)
    api_v1_router.include_router(message_attachments_router)
    api_v1_router.include_router(messages_router)
    api_v1_router.include_router(orders_router)
    api_v1_router.include_router(inventories_router)
    api_v1_router.include_router(product_registrations_router)
    api_v1_router.include_router(user_devices_router)
    api_v1_router.include_router(users_router)

    application.include_router(media_router)
    application.include_router(api_v1_router)

    return application


try:
    app = create_app()
except Exception:
    logger.exception("application.startup.failed", extra={"event_type": "application.startup.failed"})
    raise