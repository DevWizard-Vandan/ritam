"""
RITAM FastAPI WebSocket server.
Streams live predictions, agent signals, and accuracy stats to the dashboard.

Run with: uvicorn src.api.server:app --host 0.0.0.0 --port 8000 --reload
"""
import asyncio
import json
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from src.api.websocket_manager import WebSocketManager
from src.data.db import read_candles, get_connection
from src.config import settings
from loguru import logger

app = FastAPI(title="RITAM API", version="2.0")
manager = WebSocketManager()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)


@app.get("/api/candles")
def get_candles(symbol: str = "NSE:NIFTY 50", limit: int = 100):
    from pytz import timezone
    import pytz
    ist = timezone(settings.TIMEZONE)
    now = datetime.now(ist).isoformat()
    # Use a wide date range — DB will return sorted by timestamp
    candles = read_candles(symbol, "2000-01-01", now)
    return {"symbol": symbol, "candles": candles[-limit:]}


@app.get("/api/accuracy")
def get_accuracy():
    with get_connection() as conn:
        total = conn.execute("SELECT COUNT(*) FROM prediction_errors").fetchone()[0]
        correct = conn.execute(
            "SELECT COUNT(*) FROM prediction_errors WHERE direction_correct=1"
        ).fetchone()[0]
    accuracy = round(correct / total, 4) if total > 0 else None
    return {"total_predictions": total, "correct": correct, "direction_accuracy": accuracy}


@app.get("/api/agents")
def get_agent_info():
    import os
    weights_path = "config/agent_weights.json"
    if os.path.exists(weights_path):
        with open(weights_path) as f:
            return json.load(f)
    return {"weights": {}, "week_accuracy": None}


@app.websocket("/ws/predictions")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    logger.info("Dashboard client connected")
    try:
        while True:
            # Pull latest prediction from DB and broadcast
            with get_connection() as conn:
                row = conn.execute(
                    "SELECT * FROM predictions ORDER BY id DESC LIMIT 1"
                ).fetchone()
            if row:
                payload = {
                    "type": "prediction",
                    "data": {
                        "timestamp": row[1],
                        "predicted_direction": row[2],
                        "predicted_move_pct": row[3],
                        "confidence": row[4],
                        "timeframe_minutes": row[5],
                        "regime": row[6]
                    }
                }
                await manager.broadcast(json.dumps(payload))
            await asyncio.sleep(60)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("Dashboard client disconnected")
