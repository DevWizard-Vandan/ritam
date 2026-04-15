"""AnalogAgent — finds historical intraday or daily analogs for the current market window."""

from __future__ import annotations

from typing import Any

from loguru import logger

from src.agents.base import AgentBase, AgentSignal
from src.config import settings
from src.data.db import read_intraday_candles
from src.reasoning.analog_finder import find_analogs, find_intraday_analogs


class AnalogAgent(AgentBase):
    """Agent that identifies historical windows similar to the current market window.

    Prefers 15-min intraday candles when at least 20 are available.
    Falls back to daily candles when intraday data is insufficient.
    """

    name: str = "AnalogAgent"

    def collect(self) -> dict[str, Any]:
        intraday = read_intraday_candles(
            symbol=settings.INTRADAY_SYMBOL,
            limit=settings.INTRADAY_CANDLES_FOR_ANALOG,
        )
        return {"intraday_candles": intraday}

    def reason(self, data: dict[str, Any]) -> AgentSignal:
        intraday_candles: list[dict] = data.get("intraday_candles", [])

        if len(intraday_candles) >= settings.INTRADAY_CANDLES_FOR_ANALOG:
            logger.info("AnalogAgent: using intraday 15-min windows")
            analogs = find_intraday_analogs(
                current_window=intraday_candles,
                top_n=3,
                symbol=settings.INTRADAY_SYMBOL,
                window_size=settings.INTRADAY_CANDLES_FOR_ANALOG,
            )
            outcome_key = "next_5candle_return"
        else:
            logger.info("AnalogAgent: falling back to daily candles")
            from src.data.db import read_candles

            daily_candles = read_candles(
                symbol=settings.NIFTY_SYMBOL,
                from_date="2000-01-01",
                to_date="2100-01-01",
            )
            analogs = find_analogs(
                current_window=daily_candles[-20:] if len(daily_candles) >= 20 else daily_candles,
                top_n=3,
                symbol=settings.NIFTY_SYMBOL,
            )
            outcome_key = "next_5day_return"

        if not analogs:
            return AgentSignal(
                agent_name=self.name,
                signal=0,
                confidence=0.0,
                reasoning="No historical analogs found.",
                raw_data={"analogs": []},
            )

        best = analogs[0]
        outcome = best.get(outcome_key, 0.0)
        similarity = best.get("similarity_score", 0.0)

        # Derive direction from the best analog's outcome
        if outcome > 0.1:
            signal = 1
        elif outcome < -0.1:
            signal = -1
        else:
            signal = 0

        return AgentSignal(
            agent_name=self.name,
            signal=signal,
            confidence=round(float(similarity), 4),
            reasoning=(
                f"Best analog: {best.get('start_date')} to {best.get('end_date')} "
                f"(similarity={similarity:.4f}, {outcome_key}={outcome:.4f}%)"
            ),
            raw_data={"analogs": analogs},
        )
