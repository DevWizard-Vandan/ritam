"""
RITAM FastAPI WebSocket server.
Streams live predictions, agent signals, and accuracy stats to the dashboard.

Run with: uvicorn src.api.server:app --host 0.0.0.0 --port 8000 --reload
"""
import asyncio
import json
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from src.api.websocket_manager import WebSocketManager
from src.data.db import read_candles, get_connection
from src.config import settings
from src.feedback.tracker import PredictionTracker
from src.feedback.loop import FeedbackLoop
from loguru import logger
from src.reasoning.analog_finder import AnalogFinder
import datetime as dt
from src.backtest.signal_backtest import SignalBacktester

scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
scheduler_job_status = {}

def run_scheduled_cycle():
    """Runs one full orchestrator cycle. Called by scheduler."""
    import datetime as dt
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=5, minutes=30)))

    # Check if Mon-Fri
    if now.weekday() > 4:
        logger.info("Market closed — skipping cycle")
        scheduler_job_status["market_cycle"] = "skipped"
        return

    # Check market hours
    open_time = dt.datetime.strptime(settings.MARKET_OPEN_TIME, "%H:%M").time()
    close_time = dt.datetime.strptime(settings.MARKET_CLOSE_TIME, "%H:%M").time()

    if not (open_time <= now.time() <= close_time):
        logger.info("Market closed — skipping cycle")
        scheduler_job_status["market_cycle"] = "skipped"
        return

    try:
        import src.data.db as db_mod
        from src.orchestrator.agent import MarketOrchestrator
        now_iso = now.isoformat()
        candles = db_mod.read_candles(settings.NIFTY_SYMBOL, "2000-01-01", now_iso, limit=60)

        if not candles:
            logger.warning("No candles available to run cycle.")
            scheduler_job_status["market_cycle"] = "failed"
            return

        # Compute price_change_pct for the most recent candle from the preceding close.
        last_candle = dict(candles[-1])
        if len(candles) >= 2:
            prev_close = candles[-2]["close"]
            curr_close = last_candle["close"]
            last_candle["price_change_pct"] = (
                ((curr_close - prev_close) / prev_close * 100) if prev_close else 0.0
            )
        else:
            last_candle["price_change_pct"] = 0.0

        o = MarketOrchestrator()
        result = o.run_cycle(
            last_candle=last_candle,
            recent_daily_candles=candles[-20:]
        )
        logger.info(f"Scheduled cycle complete: {result.signal} "
                    f"| regime={result.regime} "
                    f"| sentiment={result.sentiment_score:.4f}")
        scheduler_job_status["market_cycle"] = "success"
    except Exception as e:
        logger.error(f"Scheduled cycle failed: {e}", exc_info=True)
        scheduler_job_status["market_cycle"] = "failed"

def resolve_outcomes_job():
    try:
        from src.learning.updater import resolve_all_pending_outcomes
        resolved = resolve_all_pending_outcomes()
        logger.info(f"Outcome resolution: {resolved} records updated")
        scheduler_job_status["outcome_resolver"] = "success"
    except Exception as e:
        logger.error(f"Outcome resolution failed: {e}", exc_info=True)
        scheduler_job_status["outcome_resolver"] = "failed"

def weight_update_job():
    try:
        from src.learning.weight_updater import run_weight_update
        result = run_weight_update()
        logger.info(
            f"Weight update complete: "
            f"{len(result['agents'])} agents updated"
        )
        scheduler_job_status["weight_updater"] = "success"
    except Exception as e:
        logger.error(f"Weight update failed: {e}", exc_info=True)
        scheduler_job_status["weight_updater"] = "failed"

@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.SCHEDULER_ENABLED:
        scheduler.add_job(
            run_scheduled_cycle,
            trigger=IntervalTrigger(minutes=settings.CYCLE_INTERVAL_MINUTES),
            id="market_cycle",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )

        def intraday_sync_job():
            from src.data.intraday_seeder import sync_intraday_today
            try:
                n = sync_intraday_today()
                logger.info(f"Intraday sync: {n} candles added")
                scheduler_job_status["intraday_sync"] = "success"
            except Exception as e:
                logger.error(f"Intraday sync failed: {e}", exc_info=True)
                scheduler_job_status["intraday_sync"] = "failed"

        scheduler.add_job(
            intraday_sync_job,
            trigger=CronTrigger(hour=9, minute=10, timezone="Asia/Kolkata"),
            id="intraday_sync",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )

        def intraday_resolve_job():
            from src.learning.intraday_resolver import resolve_intraday_outcomes
            try:
                n = resolve_intraday_outcomes()
                logger.info(f"Intraday resolution: {n} outcomes resolved")
                scheduler_job_status["intraday_resolver"] = "success"
            except Exception as e:
                logger.error(f"Intraday resolve failed: {e}", exc_info=True)
                scheduler_job_status["intraday_resolver"] = "failed"

        scheduler.add_job(
            intraday_resolve_job,
            trigger=IntervalTrigger(minutes=30),
            id="intraday_resolver",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        scheduler.add_job(
            resolve_outcomes_job,
            trigger=CronTrigger(hour=9, minute=0, timezone="Asia/Kolkata"),
            id="outcome_resolver",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        scheduler.add_job(
            weight_update_job,
            trigger=CronTrigger(day_of_week="sun", hour=0, minute=0, timezone="Asia/Kolkata"),
            id="weight_updater",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        if not scheduler.running:
            scheduler.start()
            logger.info("Scheduler started.")
    yield
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler shutdown.")

app = FastAPI(title="RITAM API", version="2.0", lifespan=lifespan)
manager = WebSocketManager()
tracker = PredictionTracker(settings.DB_PATH)
loop = FeedbackLoop(tracker)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

class OutcomePayload(BaseModel):
    timestamp: str
    actual_return_pct: float


import src.orchestrator.agent

@app.get("/api/scheduler/status")
def get_scheduler_status():
    jobs_info = []
    if settings.SCHEDULER_ENABLED:
        for job in scheduler.get_jobs():
            jobs_info.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "last_status": scheduler_job_status.get(job.id, "pending")
            })
    return {
        "scheduler_enabled": settings.SCHEDULER_ENABLED,
        "cycle_interval_minutes": settings.CYCLE_INTERVAL_MINUTES,
        "market_hours": f"{settings.MARKET_OPEN_TIME}–{settings.MARKET_CLOSE_TIME} IST Mon–Fri",
        "jobs": jobs_info
    }


@app.get("/api/explanation/latest")
def get_latest_explanation():
    return src.orchestrator.agent.LATEST_EXPLANATION

@app.get("/api/feedback/accuracy")
def get_feedback_accuracy():
    return tracker.get_accuracy_stats()


@app.post("/api/feedback/outcome")
def post_outcome(payload: OutcomePayload):
    try:
        tracker.record_outcome(timestamp=payload.timestamp, actual_return_pct=payload.actual_return_pct)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "ok", "timestamp": payload.timestamp}


@app.post("/api/feedback/resolve/{timestamp}")
def resolve_outcome(timestamp: str):
    try:
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid timestamp format")
    result = loop.resolve_outcome(timestamp)
    if result is None:
        raise HTTPException(status_code=404, detail="No prediction or candles found for outcome resolution")
    return result


@app.get("/api/analogs")
def get_analogs(top_n: int = 3):
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=5, minutes=30))).isoformat()
    candles = read_candles(settings.NIFTY_SYMBOL, "2000-01-01", now)[-20:]
    finder = AnalogFinder(settings.DB_PATH)
    return finder.find_analogs(candles, top_n=top_n)


@app.get("/api/candles")
def get_candles(symbol: str = "NSE:NIFTY 50", limit: int = 100):
    from pytz import timezone
    import pytz
    ist = timezone(settings.TIMEZONE)
    now = datetime.now(ist).isoformat()
    # Use a wide date range — DB will return sorted by timestamp
    candles = read_candles(symbol, "2000-01-01", now)
    return {"symbol": symbol, "candles": candles[-limit:]}


@app.get("/api/intraday/candles")
def get_intraday_candles(symbol: str = "NSE:NIFTY 50", limit: int = 50):
    from src.data.db import read_intraday_candles

    limit = min(max(limit, 1), 200)
    candles = read_intraday_candles(symbol, limit=limit)
    return {
        "symbol": symbol,
        "count": len(candles),
        "candles": candles
    }

@app.get("/api/intraday/stats")
def get_intraday_stats():
    from src.data.db import read_intraday_candles, get_latest_intraday_timestamp

    symbol = settings.INTRADAY_SYMBOL
    candles = read_intraday_candles(symbol)

    total = len(candles)
    earliest = candles[0]["timestamp_ist"] if total > 0 else None
    latest = get_latest_intraday_timestamp(symbol)

    return {
        "symbol": symbol,
        "total_candles": total,
        "earliest": earliest,
        "latest": latest,
        "last_sync": latest,
        "resolution_mode": "intraday" if settings.USE_INTRADAY else "daily"
    }


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


@app.get("/api/agents/stats")
def get_agents_stats():
    from src.data.db import get_agent_accuracy_stats
    import pytz
    from datetime import datetime, timezone, timedelta

    try:
        ist = pytz.timezone("Asia/Kolkata")
        now = datetime.now(ist).isoformat()
    except ImportError:
        ist = timezone(timedelta(hours=5, minutes=30))
        now = datetime.now(ist).isoformat()

    return {
        "updated_at": now,
        "agents": get_agent_accuracy_stats()
    }


@app.get("/api/weights/history")
def get_weights_history(agent: str, limit: int = 10):
    from src.data.db import get_connection
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT weight, accuracy_7d, recorded_at FROM weight_history WHERE agent_name = ? ORDER BY recorded_at DESC LIMIT ?",
            (agent, limit)
        ).fetchall()
    return [
        {
            "weight": row[0],
            "accuracy_7d": row[1],
            "recorded_at": row[2]
        }
        for row in rows
    ]


@app.post("/api/weights/update")
def trigger_weight_update():
    from src.learning.weight_updater import run_weight_update
    return run_weight_update()



@app.get("/api/paper/trades")
def get_paper_trades(limit: int = 50):
    from src.data.db import read_paper_trades
    return read_paper_trades(limit=limit)

@app.get("/api/paper/stats")
def get_paper_stats():
    from src.paper_trading.engine import PaperTradingEngine
    engine = PaperTradingEngine()
    return engine.get_stats()


@app.get("/api/backtest/latest")
def get_latest_backtest():
    reports_dir = Path("reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    html_reports = sorted(reports_dir.glob("backtest_*.html"), key=lambda p: p.stat().st_mtime)

    if html_reports:
        latest = html_reports[-1]
        content = latest.read_text(encoding="utf-8")
        start_tag = '<script id="backtest-result" type="application/json">'
        end_tag = "</script>"
        start_idx = content.find(start_tag)
        if start_idx != -1:
            start_idx += len(start_tag)
            end_idx = content.find(end_tag, start_idx)
            if end_idx != -1:
                payload = content[start_idx:end_idx].strip()
                return json.loads(payload)

    now = datetime.utcnow()
    from_date = (now - dt.timedelta(days=90)).date().isoformat()
    to_date = now.date().isoformat()
    result = SignalBacktester().run(from_date=from_date, to_date=to_date, walk_forward=False)
    return SignalBacktester.to_dict(result)

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
