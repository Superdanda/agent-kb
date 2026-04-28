import asyncio
import logging
import threading
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from starlette.websockets import WebSocket

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WebhookStreamConnection:
    task_id: str
    websocket: WebSocket
    loop: asyncio.AbstractEventLoop


class WebhookStreamHub:
    """In-memory fan-out for KB->Agent webhook response chunks."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._connections: dict[str, list[WebhookStreamConnection]] = {}
        self._history: dict[str, deque[dict[str, Any]]] = {}

    async def connect(self, task_id: str, websocket: WebSocket) -> WebhookStreamConnection:
        await websocket.accept()
        connection = WebhookStreamConnection(
            task_id=task_id,
            websocket=websocket,
            loop=asyncio.get_running_loop(),
        )
        with self._lock:
            self._connections.setdefault(task_id, []).append(connection)
            history = list(self._history.get(task_id, ()))
        await websocket.send_json({
            "type": "connected",
            "task_id": task_id,
            "timestamp": _now_iso(),
        })
        for event in history:
            await websocket.send_json(event)
        return connection

    def disconnect(self, connection: WebhookStreamConnection) -> None:
        with self._lock:
            connections = self._connections.get(connection.task_id)
            if not connections:
                return
            self._connections[connection.task_id] = [
                item for item in connections if item.websocket is not connection.websocket
            ]
            if not self._connections[connection.task_id]:
                self._connections.pop(connection.task_id, None)

    def publish(self, task_id: str | None, event: dict[str, Any]) -> None:
        if not task_id:
            return
        payload = {
            "task_id": task_id,
            "timestamp": _now_iso(),
            **event,
        }
        with self._lock:
            self._history.setdefault(task_id, deque(maxlen=200)).append(payload)
            connections = list(self._connections.get(task_id, ()))
        for connection in connections:
            self._schedule_send(connection, payload)

    def _schedule_send(self, connection: WebhookStreamConnection, payload: dict[str, Any]) -> None:
        async def _send() -> None:
            try:
                await connection.websocket.send_json(payload)
            except Exception as exc:
                logger.debug("Dropping webhook stream websocket: %s", exc)
                self.disconnect(connection)

        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None

        if running_loop is connection.loop:
            connection.loop.create_task(_send())
            return

        try:
            asyncio.run_coroutine_threadsafe(_send(), connection.loop)
        except RuntimeError:
            self.disconnect(connection)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


webhook_stream_hub = WebhookStreamHub()
