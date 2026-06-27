"""In-process pub/sub for realtime message/card events delivered over SSE.

The backend runs a single uvicorn worker, so an in-memory broker is sufficient: publishers
(sync request handlers running in the threadpool) hand events to subscribers (the async SSE
generators running on the event loop). If this ever scales to multiple workers/replicas, swap
the broker body for a shared transport (Postgres LISTEN/NOTIFY or Redis) behind this same API.
"""

from __future__ import annotations

import asyncio
import logging
import threading

logger = logging.getLogger("app.message_stream")

# Bound per subscriber: a stuck client drops events rather than growing memory unbounded.
# It recovers the missed events through delta-sync on its next /messages/sync call.
_QUEUE_MAXSIZE = 200


class MessageStreamBroker:
    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._subscribers: set[asyncio.Queue] = set()
        self._lock = threading.Lock()

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Capture the event loop at startup so threadpool publishers can schedule onto it."""
        self._loop = loop

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=_QUEUE_MAXSIZE)
        with self._lock:
            self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        with self._lock:
            self._subscribers.discard(queue)

    def publish(self, event: dict) -> None:
        """Fan an event out to all subscribers. Safe to call from any thread."""
        loop = self._loop
        if loop is None:
            return
        with self._lock:
            subscribers = list(self._subscribers)
        for queue in subscribers:
            loop.call_soon_threadsafe(self._put_nowait, queue, event)

    @staticmethod
    def _put_nowait(queue: asyncio.Queue, event: dict) -> None:
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            logger.warning("message_stream.drop", extra={"event_type": "message_stream.drop"})


broker = MessageStreamBroker()
