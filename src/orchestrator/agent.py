"""Simple market orchestrator that fuses sentiment, regime, and analog signals."""
from __future__ import annotations

from dataclasses import dataclass

from src.data.news_fetcher import fetch_headlines
from src.reasoning.analog_finder import find_analogs
from src.reasoning.regime_classifier import classify_regime
from src.sentiment.scorer import score_headlines


@dataclass
class OrchestratorResult:
    regime: str
    sentiment_score: float
    top_analogs: list[dict]
    signal: str


class MarketOrchestrator:
    """Coordinate pipeline steps and output one actionable signal per cycle."""

    def __init__(self, analog_top_n: int = 3):
        self.analog_top_n = analog_top_n

    def run_cycle(self, last_candle: dict, recent_daily_candles: list[dict], vix: float = 15.0) -> OrchestratorResult:
        """
        Run one orchestration cycle.

        Args:
            last_candle: Latest candle with at least `price_change_pct`.
            recent_daily_candles: Last 20 daily candles used for analog matching.
            vix: Current India VIX estimate.
        """
        headlines = fetch_headlines()
        scored = score_headlines(headlines)

        if scored:
            sentiment_score = sum(item["score"] for item in scored) / len(scored)
        else:
            sentiment_score = 0.0

        regime = classify_regime(
            price_change_pct=float(last_candle.get("price_change_pct", 0.0)),
            vix=vix,
            news_count=len(headlines),
            sentiment=sentiment_score,
        )

        top_analogs = find_analogs(recent_daily_candles, top_n=self.analog_top_n)
        signal = self._derive_signal(regime=regime, sentiment_score=sentiment_score)

        return OrchestratorResult(
            regime=regime,
            sentiment_score=sentiment_score,
            top_analogs=top_analogs,
            signal=signal,
        )

    @staticmethod
    def _derive_signal(regime: str, sentiment_score: float) -> str:
        if regime in {"trending_up", "recovery"} and sentiment_score > 0.1:
            return "buy"
        if regime in {"crisis", "trending_down"} and sentiment_score < -0.1:
            return "sell"
        return "hold"
