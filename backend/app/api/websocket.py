"""
SENTINEL AI X — WebSocket endpoint for live Digital Twin updates.

Clients subscribe to a repository's Digital Twin by connecting to:
  WS /api/v1/ws/digital-twin/{repo_id}

The server broadcasts a compact diff message on every GitHub event
that modifies the graph, so the frontend can update without polling.
"""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from typing import Any

import structlog
from fastapi import WebSocket, WebSocketDisconnect

logger = structlog.get_logger()


# ─────────────────────────────────────────────────────────────────
# Connection Manager
# ─────────────────────────────────────────────────────────────────


class DigitalTwinConnectionManager:
    """
    Manages WebSocket connections grouped by repository ID.

    Thread-safe via asyncio.Lock — safe for concurrent FastAPI workers.
    """

    def __init__(self) -> None:
        # repo_id → set of active WebSocket connections
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, repo_id: str, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._connections[repo_id].add(ws)
        logger.info("WebSocket connected", repo_id=repo_id,
                    total=len(self._connections[repo_id]))

    async def disconnect(self, repo_id: str, ws: WebSocket) -> None:
        async with self._lock:
            self._connections[repo_id].discard(ws)
            if not self._connections[repo_id]:
                del self._connections[repo_id]
        logger.info("WebSocket disconnected", repo_id=repo_id)

    async def broadcast(self, repo_id: str, message: dict[str, Any]) -> None:
        """Send a message to all clients subscribed to a repository."""
        payload = json.dumps(message)
        dead: list[WebSocket] = []
        async with self._lock:
            sockets = set(self._connections.get(repo_id, set()))

        for ws in sockets:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)

        # Clean up dead connections
        if dead:
            async with self._lock:
                for ws in dead:
                    self._connections[repo_id].discard(ws)

    def subscriber_count(self, repo_id: str) -> int:
        return len(self._connections.get(repo_id, set()))


# Module-level singleton
twin_ws_manager = DigitalTwinConnectionManager()


# ─────────────────────────────────────────────────────────────────
# WebSocket Endpoint Handler
# ─────────────────────────────────────────────────────────────────


async def digital_twin_ws_handler(ws: WebSocket, repo_id: str) -> None:
    """
    Handle a WebSocket connection for a repository's Digital Twin.

    Protocol:
      - On connect: server sends current subscriber count
      - Server pushes "twin_update" messages when graph changes
      - Client can send "ping" → server replies "pong"
      - On disconnect: connection removed silently
    """
    await twin_ws_manager.connect(repo_id, ws)
    try:
        # Send welcome with current subscriber count
        await ws.send_text(json.dumps({
            "type": "connected",
            "repo_id": repo_id,
            "subscribers": twin_ws_manager.subscriber_count(repo_id),
        }))

        # Keep connection alive, handle client messages
        while True:
            try:
                data = await asyncio.wait_for(ws.receive_text(), timeout=30.0)
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await ws.send_text(json.dumps({"type": "pong"}))
            except asyncio.TimeoutError:
                # Send heartbeat to detect dead connections
                await ws.send_text(json.dumps({"type": "heartbeat"}))
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.warning("WebSocket error", repo_id=repo_id, error=str(exc))
    finally:
        await twin_ws_manager.disconnect(repo_id, ws)


# ─────────────────────────────────────────────────────────────────
# Broadcast Helpers (called by Celery tasks / event handlers)
# ─────────────────────────────────────────────────────────────────


async def broadcast_twin_update(
    repo_id: str,
    event_type: str,
    stats: dict[str, int],
    nodes_affected: list[str] | None = None,
) -> None:
    """
    Broadcast a Digital Twin update to all subscribed frontend clients.

    Called after each successful graph mutation.
    """
    if twin_ws_manager.subscriber_count(repo_id) == 0:
        return  # No subscribers, skip serialisation overhead

    await twin_ws_manager.broadcast(repo_id, {
        "type": "twin_update",
        "repo_id": repo_id,
        "event_type": event_type,
        "stats": stats,
        "nodes_affected": nodes_affected or [],
    })
