import asyncio
import json
import logging
from typing import Any, Dict, Set

logger = logging.getLogger(__name__)


class EventBroadcaster:
    """Thread-safe and async-compatible Server-Sent Events (SSE) broadcaster."""

    def __init__(self):
        self._subscribers: Set[asyncio.Queue] = set()
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_loop(self, loop: asyncio.AbstractEventLoop):
        self._loop = loop

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.add(q)
        logger.info(f"New SSE subscriber added. Total subscribers: {len(self._subscribers)}")
        return q

    def unsubscribe(self, q: asyncio.Queue):
        if q in self._subscribers:
            self._subscribers.remove(q)
            logger.info(f"SSE subscriber removed. Total subscribers: {len(self._subscribers)}")

    def broadcast(self, event_type: str, payload: Dict[str, Any]):
        """Broadcast an event to all connected SSE clients."""
        message = {
            "type": event_type,
            "payload": payload,
        }
        raw_msg = json.dumps(message)
        dead_subscribers = []

        for q in list(self._subscribers):
            try:
                q.put_nowait(raw_msg)
            except Exception:
                dead_subscribers.append(q)

        for q in dead_subscribers:
            self.unsubscribe(q)


broadcaster = EventBroadcaster()
