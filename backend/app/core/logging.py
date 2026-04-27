import json
import logging
import sys
import time
from datetime import datetime, timezone

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from app.core.config import APP_ENV, LOG_LEVEL, SENTRY_DSN, SENTRY_ENVIRONMENT, SENTRY_TRACES_SAMPLE_RATE
from app.core.request_context import get_request_context


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        context = get_request_context()
        if context.get("request_id"):
            payload["request_id"] = context["request_id"]
        if context.get("ip_address"):
            payload["client_ip"] = context["ip_address"]
        if context.get("user_agent"):
            payload["user_agent"] = context["user_agent"]
        if context.get("user_id"):
            payload["user_id"] = context["user_id"]

        for field in (
            "path",
            "method",
            "status_code",
            "duration_ms",
            "event_type",
            "user_id",
            "auth_login",
            "session_id",
            "error_code",
        ):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=True)


def configure_logging() -> None:
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.propagate = True


def init_error_tracking() -> None:
    if not SENTRY_DSN:
        return

    sentry_logging = LoggingIntegration(level=logging.INFO, event_level=logging.ERROR)

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=SENTRY_ENVIRONMENT or APP_ENV,
        traces_sample_rate=SENTRY_TRACES_SAMPLE_RATE,
        integrations=[sentry_logging, FastApiIntegration(), SqlalchemyIntegration()],
        send_default_pii=False,
    )


def log_request(logger: logging.Logger, *, method: str, path: str, status_code: int, started_at: float, user_id: int | str | None = None) -> None:
    duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
    level = logging.ERROR if status_code >= 500 else logging.WARNING if status_code >= 400 else logging.INFO
    logger.log(
        level,
        "request.completed",
        extra={
            "event_type": "request.completed",
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": duration_ms,
            "user_id": user_id,
        },
    )