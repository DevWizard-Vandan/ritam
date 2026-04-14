"""Simple market orchestrator that fuses sentiment, regime, and analog signals."""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from src.data.news_fetcher import fetch_headlines
from loguru import logger
from src.reasoning.analog_finder import find_analogs
from src.reasoning.regime_classifier import classify_regime
from src.sentiment.scorer import score_headlines
from src.feedback.loop import FeedbackLoop
from src.feedback.tracker import PredictionTracker
from src.config import settings
from src.reasoning.analog_explainer import AnalogExplainer

# Hard deadline for all concurrent agents.
# NewsImpactAgent is the slowest (network + FinBERT + Gemini) and has a
# 25-second per-agent budget; the overall budget is 28s to leave 3s margin.
_AGENT_EXECUTION_DEADLINE_SECONDS: int = 28

# Synthesis confidence thresholds for triggering the weighted fallback
_SYNTHESIS_MIN_CONFIDENCE: float = 0.15
_SYNTHESIS_ZERO_SIGNAL_MAX_CONFIDENCE: float = 0.10

_ECONOMIC_CALENDAR_UNCERTAINTY_MULTIPLIER: float = 0.20

LATEST_EXPLANATION = ""


def _weighted_fallback(
    agent_signals: list, regime: str
) -> "AgentSignal":
    """
    Computes a weighted vote from all agent signals when
    MacroSynthesisAgent is unavailable.

    Weight rules:
      FIIDerivativeAgent:    0.25  (strongest institutional signal)
      MarketBreadthAgent:    0.20
      TechnicalPatternAgent: 0.20
      RegimeCrossCheckAgent: 0.15
      NewsImpactAgent:       0.10
      OptionsChainAgent:     0.05
      SectorRotationAgent:   0.03
      GlobalMarketAgent:     0.02
      EconomicCalendarAgent: 0.00  (uncertainty flag only)
    Default weight for unknown agents: 0.01
    """
    from src.agents.base import AgentSignal

    WEIGHTS = {
        "FIIDerivativeAgent": 0.25,
        "MarketBreadthAgent": 0.20,
        "TechnicalPatternAgent": 0.20,
        "RegimeCrossCheckAgent": 0.15,
        "NewsImpactAgent": 0.10,
        "OptionsChainAgent": 0.05,
        "SectorRotationAgent": 0.03,
        "GlobalMarketAgent": 0.02,
        "EconomicCalendarAgent": 0.00,
    }

    # Check for EconomicCalendarAgent uncertainty penalty
    eco = next(
        (s for s in agent_signals
         if s.agent_name == "EconomicCalendarAgent"),
        None
    )
    uncertainty_penalty = eco.confidence * _ECONOMIC_CALENDAR_UNCERTAINTY_MULTIPLIER if eco else 0.0

    weighted_sum = 0.0
    total_weight = 0.0
    for sig in agent_signals:
        w = WEIGHTS.get(sig.agent_name, 0.01)
        if w == 0.0:
            continue
        weighted_sum += sig.signal * sig.confidence * w
        total_weight += w

    if total_weight == 0:
        raw_score = 0.0
    else:
        raw_score = weighted_sum / total_weight

    # Crisis override
    if regime == "crisis":
        final_signal = -1
        final_conf = 0.70
        reasoning = (f"[Fallback] Crisis regime override. "
                     f"Raw weighted score: {raw_score:.3f}")
    elif raw_score > 0.15:
        final_signal = 1
        final_conf = min(abs(raw_score) * 0.8, 0.75)
        reasoning = (f"[Fallback] Weighted bullish: {raw_score:.3f}. "
                     f"Regime: {regime}")
    elif raw_score < -0.15:
        final_signal = -1
        final_conf = min(abs(raw_score) * 0.8, 0.75)
        reasoning = (f"[Fallback] Weighted bearish: {raw_score:.3f}. "
                     f"Regime: {regime}")
    else:
        final_signal = 0
        final_conf = 0.30
        reasoning = (f"[Fallback] Weighted neutral: {raw_score:.3f}. "
                     f"Regime: {regime}")

    # Apply uncertainty penalty
    final_conf = max(0.10, final_conf - uncertainty_penalty)

    return AgentSignal(
        agent_name="WeightedFallback",
        signal=final_signal,
        confidence=round(final_conf, 3),
        reasoning=reasoning,
        raw_data={"raw_score": raw_score, "regime": regime}
    )

@dataclass
class OrchestratorResult:
    regime: str
    sentiment_score: float
    top_analogs: list[dict]
    signal: str
    explanation: str = ""
    agent_signals: list[dict] = field(default_factory=list)
    synthesis_reasoning: str = ""
    final_confidence: float = 0.0
    source: str = "daily"


class MarketOrchestrator:
    """Coordinate pipeline steps and output one actionable signal per cycle."""

    def __init__(
        self,
        analog_top_n: int = 3,
        tracker: PredictionTracker | None = None,
        loop: FeedbackLoop | None = None,
    ):
        self.analog_top_n = analog_top_n
        self.tracker = tracker or PredictionTracker(settings.DB_PATH)
        self.loop = loop or FeedbackLoop(self.tracker)
        self.explainer = AnalogExplainer()

    def run_cycle(
        self,
        last_candle: dict | None = None,
        recent_daily_candles: list[dict] | None = None,
        vix: float = 15.0,
    ) -> OrchestratorResult:
        """
        Run one orchestration cycle.

        Args:
            last_candle: Latest candle with at least `price_change_pct`.
                         Optional — auto-fetched from intraday DB when USE_INTRADAY=True.
            recent_daily_candles: Last 20 daily candles for analog matching.
                                  Optional — auto-fetched when USE_INTRADAY=True.
            vix: Current India VIX estimate.
        """
        source = "daily"

        if settings.USE_INTRADAY:
            from src.data.db import read_intraday_candles
            intraday_candles = read_intraday_candles(
                settings.INTRADAY_SYMBOL,
                limit=settings.INTRADAY_CANDLES_FOR_ANALOG + 5,
            )
            if len(intraday_candles) < 10:
                logger.warning("Insufficient intraday candles — falling back to daily")
            else:
                source = "intraday"
                if len(intraday_candles) >= 2:
                    prev_close = intraday_candles[-2]["close"]
                    curr_close = intraday_candles[-1]["close"]
                    price_change = (
                        (curr_close - prev_close) / prev_close * 100
                        if prev_close else 0.0
                    )
                else:
                    price_change = 0.0
                last_candle = intraday_candles[-1].copy()
                last_candle["price_change_pct"] = price_change
                recent_daily_candles = intraday_candles[-(settings.INTRADAY_CANDLES_FOR_ANALOG):]

        # Final fallback: if still None (daily mode or intraday fallback), fetch daily candles
        if last_candle is None or recent_daily_candles is None:
            from src.data.db import read_candles
            from datetime import date, timedelta
            to_date = str(date.today())
            from_date = str(date.today() - timedelta(days=120))
            daily = read_candles(settings.INTRADAY_SYMBOL, from_date, to_date)
            if not daily:
                logger.error("No daily candles available — cannot run cycle")
                raise RuntimeError("No candle data available for run_cycle()")
            if last_candle is None:
                last_candle = daily[-1].copy()
                if "price_change_pct" not in last_candle and len(daily) >= 2:
                    prev = daily[-2]["close"]
                    curr = daily[-1]["close"]
                    last_candle["price_change_pct"] = (
                        (curr - prev) / prev * 100 if prev else 0.0
                    )
            if recent_daily_candles is None:
                recent_daily_candles = daily[-20:]

        headlines = fetch_headlines()
        scored = score_headlines(headlines)

        if scored:
            sentiment_score = sum(item["score"] for item in scored) / len(scored)
        else:
            sentiment_score = 0.0

        sentiment_score = round(sentiment_score, 4)

        regime = classify_regime(
            price_change_pct=float(last_candle.get("price_change_pct", 0.0)),
            vix=vix,
            news_count=len(headlines),
            sentiment=sentiment_score,
        )

        # TODO: preload historical candles once per instance to avoid full DB scan on every run_cycle() call
        top_analogs = find_analogs(recent_daily_candles, top_n=self.analog_top_n)

        from src.agents.factory import build_agents, build_synthesis_agent
        from concurrent.futures import ThreadPoolExecutor, TimeoutError

        agents = build_agents()
        agent_signals = []
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = {executor.submit(a.run): a for a in agents}
            deadline = time.time() + _AGENT_EXECUTION_DEADLINE_SECONDS

            for future, agent in list(futures.items()):
                remaining = deadline - time.time()
                if remaining <= 0:
                    logger.warning(f"Agent {agent.name} skipped — deadline exceeded")
                    future.cancel()
                    continue
                try:
                    result = future.result(timeout=remaining)
                    agent_signals.append(result)
                except TimeoutError:
                    logger.warning(f"Agent {agent.name} timed out")
                    future.cancel()
                except Exception as e:
                    logger.warning(f"Agent {agent.name} failed: {e}")

        synth_agent = build_synthesis_agent()
        analog_summary = (
            f"Top analog: {top_analogs[0]['start_date']} "
            f"similarity={top_analogs[0]['similarity_score']:.3f} "
            f"5d_return={top_analogs[0]['next_5day_return']:.2f}%"
            if top_analogs else "No analogs found"
        )
        synthesis = synth_agent.reason({
            "agent_signals": agent_signals,
            "regime": regime,
            "analog_summary": analog_summary,
        })

        # If synthesis failed (empty response / exhausted keys)
        # compute weighted signal from agent signals directly
        if synthesis.confidence < _SYNTHESIS_MIN_CONFIDENCE or (
            synthesis.signal == 0 and synthesis.confidence <= _SYNTHESIS_ZERO_SIGNAL_MAX_CONFIDENCE
        ):
            synthesis = _weighted_fallback(agent_signals, regime)
            logger.warning(
                "MacroSynthesis failed — using weighted agent fallback"
            )

        if synthesis.signal == 1:
            signal = "buy"
        elif synthesis.signal == -1:
            signal = "sell"
        else:
            signal = "hold"

        final_confidence = synthesis.confidence

        from src.data.db import log_agent_signals
        import uuid
        cycle_id = str(uuid.uuid4())
        log_agent_signals(cycle_id=cycle_id, signals=agent_signals + [synthesis])

        explanation = self.explainer.explain(recent_daily_candles, top_analogs, regime, sentiment_score)
        logger.info(f"Explanation: {explanation[:100]}...")

        global LATEST_EXPLANATION
        LATEST_EXPLANATION = explanation

        result = OrchestratorResult(
            regime=regime,
            sentiment_score=sentiment_score,
            top_analogs=top_analogs,
            signal=signal,
            explanation=explanation,
            agent_signals=[s.__dict__ for s in agent_signals],
            synthesis_reasoning=synthesis.reasoning,
            final_confidence=final_confidence,
            source=source,
        )

        timestamp = self.loop.record_prediction(result)
        logger.info(f"Prediction recorded: {signal} at {timestamp}")

        return result

    @staticmethod
    def _derive_signal(regime: str, sentiment_score: float) -> str:
        if regime in {"trending_up", "recovery"} and sentiment_score > 0.1:
            return "buy"
        if regime in {"crisis", "trending_down"} and sentiment_score < -0.1:
            return "sell"
        return "hold"
