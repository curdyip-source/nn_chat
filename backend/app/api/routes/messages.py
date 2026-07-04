import asyncio
import json

from fastapi import APIRouter, Depends, Header, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, get_db
from app.dependencies.auth import get_current_session, get_current_user
from app.schemas.messages import MessageCreatePayload, MessageUpdatePayload
from app.services.message_stream import broker
from app.services.messages import create_message, delete_message, list_messages, sync_messages, update_message

router = APIRouter(prefix="/messages", tags=["messages"])

# Seconds between SSE heartbeats — keeps the connection (and any proxy) alive between events.
_SSE_HEARTBEAT_SECONDS = 20


@router.get("")
def get_messages(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    before_message_id: int | None = Query(default=None, ge=1),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
) -> dict:
    return list_messages(db, current_user, before_message_id=before_message_id, page=page, page_size=page_size)


@router.get("/sync")
def sync_messages_route(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
) -> dict:
    return sync_messages(db, current_user, cursor=cursor, limit=limit)


@router.get("/stream")
async def stream_messages_route(request: Request, authorization: str | None = Header(default=None)) -> StreamingResponse:
    # Validate auth with a short-lived session so the stream doesn't hold a pooled DB connection
    # for its whole lifetime.
    auth_db = SessionLocal()
    try:
        get_current_session(authorization, auth_db)
    finally:
        auth_db.close()

    queue = broker.subscribe()

    async def event_generator():
        try:
            yield ": connected\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=_SSE_HEARTBEAT_SECONDS)
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
        finally:
            broker.unsubscribe(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@router.post("", status_code=status.HTTP_201_CREATED)
def create_message_route(payload: MessageCreatePayload, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return {"item": create_message(db, payload, current_user)}


@router.put("/{message_id}")
def update_message_route(message_id: int, payload: MessageUpdatePayload, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return {"item": update_message(db, message_id, payload, current_user)}


@router.delete("/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_message_route(message_id: int, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)) -> None:
    delete_message(db, message_id, current_user)