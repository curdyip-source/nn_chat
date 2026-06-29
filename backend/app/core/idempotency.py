"""Idempotency-Key middleware.

A client that re-sends a non-idempotent POST after a lost response (flaky network / VPN drop)
would otherwise create a duplicate (duplicate orders / chat messages / attachments). When a request
carries an ``Idempotency-Key`` header we capture the first successful response keyed by that value
and replay it verbatim for any later request with the same key, so the write happens exactly once.
"""

import logging

from fastapi import Request
from fastapi.responses import Response
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal
from app.models.idempotency_keys import IdempotencyKey


logger = logging.getLogger("app.idempotency")

IDEMPOTENCY_HEADER = "Idempotency-Key"
_MAX_KEY_LENGTH = 255


async def idempotency_middleware(request: Request, call_next):
    if request.method != "POST":
        return await call_next(request)

    key = request.headers.get(IDEMPOTENCY_HEADER)
    if not key or len(key) > _MAX_KEY_LENGTH:
        return await call_next(request)

    replay = _load_captured_response(key)
    if replay is not None:
        status_code, body = replay
        return Response(
            content=body,
            status_code=status_code,
            media_type="application/json",
            headers={"Idempotency-Replayed": "true"},
        )

    response = await call_next(request)

    # Buffer the streamed body so it can be both persisted and returned to the client.
    body = b""
    async for chunk in response.body_iterator:
        body += chunk

    if 200 <= response.status_code < 300:
        _store_captured_response(
            key=key,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            body=body,
            user_id=getattr(request.state, "user_id", None),
        )

    headers = dict(response.headers)
    headers.pop("content-length", None)  # recomputed for the rebuilt body
    return Response(content=body, status_code=response.status_code, headers=headers)


def _load_captured_response(key: str) -> tuple[int, bytes] | None:
    db = SessionLocal()
    try:
        row = db.query(IdempotencyKey).filter(IdempotencyKey.idempotency_key_value == key).first()
        if row is None:
            return None
        return row.idempotency_key_status_code, row.idempotency_key_response.encode("utf-8")
    except Exception:
        logger.exception("idempotency.load_failed", extra={"event_type": "idempotency.load_failed"})
        return None
    finally:
        db.close()


def _store_captured_response(*, key: str, method: str, path: str, status_code: int, body: bytes, user_id: int | None) -> None:
    try:
        response_text = body.decode("utf-8")
    except UnicodeDecodeError:
        # Non-text response (unexpected for create endpoints) — skip caching, still returned live.
        return

    db = SessionLocal()
    try:
        db.add(
            IdempotencyKey(
                idempotency_key_value=key,
                idempotency_key_user_id=user_id,
                idempotency_key_method=method,
                idempotency_key_path=path[:255],
                idempotency_key_status_code=status_code,
                idempotency_key_response=response_text,
            )
        )
        db.commit()
    except IntegrityError:
        # A concurrent request with the same key already captured the response — that one wins.
        db.rollback()
    except Exception:
        db.rollback()
        logger.exception("idempotency.store_failed", extra={"event_type": "idempotency.store_failed"})
    finally:
        db.close()
