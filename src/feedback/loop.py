import logging
from datetime import datetime, timezone, timedelta
from typing import TYPE_CHECKING
from src.feedback.tracker import PredictionTracker
from src.data.db import read_candles

if TYPE_CHECKING:
    from src.orchestrator.agent import OrchestratorResult

logger = logging.getLogger(__name__)

class FeedbackLoop:
    def __init__(self, tracker: PredictionTracker, symbol: str = "NSE:NIFTY 50"):
        self.tracker = tracker
        self.symbol = symbol

    def record_prediction(self, result: "OrchestratorResult") -> str:
        ist_tz = timezone(timedelta(hours=5, minutes=30))
        timestamp = datetime.now(ist_tz).isoformat()
        analog_similarity = result.top_analogs[0].get("similarity_score", 0.0) if result.top_analogs else 0.0

        self.tracker.record_prediction(
            timestamp=timestamp,
            signal=result.signal,
            sentiment_score=result.sentiment_score,
            regime=result.regime,
            analog_similarity=analog_similarity
        )
        return timestamp

    def resolve_outcome(self, timestamp: str) -> dict | None:
        try:
            entry_date = datetime.fromisoformat(timestamp)
        except ValueError:
            logger.error(f"Invalid timestamp format: {timestamp}")
            return None

        next_day_iso = (entry_date + timedelta(days=1)).isoformat()

        candles = read_candles(self.symbol, timestamp, next_day_iso)

        if not candles or len(candles) < 2:
            return None

        entry_candle = candles[0]
        next_candle = candles[-1]

        entry_close = entry_candle["close"]
        next_close = next_candle["close"]

        if entry_close == 0:
            return None

        actual_return_pct = (next_close - entry_close) / entry_close * 100

        self.tracker.record_outcome(timestamp, actual_return_pct)

        return {
            "timestamp": timestamp,
            "actual_return_pct": actual_return_pct
        }
