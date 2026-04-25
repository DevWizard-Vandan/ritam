"""Manages active WebSocket connections for the RITAM dashboard."""
from fastapi import WebSocket
try:
    from loguru import logger
except ModuleNotFoundError:  # pragma: no cover - local fallback
    import logging
    logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)
        logger.info(f"WS connected. Active clients: {len(self.active)}")

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)
        logger.info(f"WS disconnected. Active clients: {len(self.active)}")

    async def broadcast(self, message: str):
        dead = []
        for ws in self.active:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)
