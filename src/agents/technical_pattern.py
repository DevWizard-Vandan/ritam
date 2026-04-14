from src.agents.base import AgentBase, AgentSignal
from loguru import logger

class TechnicalPatternAgent(AgentBase):
    name = "TechnicalPatternAgent"
    # assigned_api_key set from settings.GEMINI_API_KEY_3 at runtime

    def collect(self) -> dict:
        """Reads last 25 candles from DB."""
        from src.data.db import read_candles
        from datetime import date, timedelta
        to_date = str(date.today())
        from_date = str(date.today() - timedelta(days=60))
        candles = read_candles("NSE:NIFTY 50", from_date, to_date)
        return {"candles": candles[-25:] if len(candles) >= 25 else candles}

    def reason(self, data: dict) -> AgentSignal:
        from src.config import settings
        candles = data.get("candles", [])
        if len(candles) < 10:
            return AgentSignal(
                agent_name=self.name, signal=0,
                confidence=0.0, reasoning="Insufficient candle data",
                raw_data=data
            )
        candle_summary = "\n".join(
            f"{c.get('timestamp_ist','')[:10]}: O={c.get('open'):.0f} "
            f"H={c.get('high'):.0f} L={c.get('low'):.0f} "
            f"C={c.get('close'):.0f}"
            for c in candles[-15:]
        )
        model = (settings.GEMINI_PRO_MODEL if settings.GEMINI_USE_PRO
                 else settings.GEMINI_FLASH_LITE_MODEL)
        prompt = f"""Analyze this Nifty 50 OHLC data (last 15 daily candles):

{candle_summary}

Identify:
1. Primary trend direction (uptrend/downtrend/sideways)
2. Key pattern if any (flag, wedge, double top/bottom, triangle, etc.)
3. Key support level (price)
4. Key resistance level (price)
5. Short-term bias for next 1-3 days

Respond ONLY with valid JSON, no markdown:
{{"trend": "up|down|sideways", "pattern": "name or none",
  "support": number, "resistance": number,
  "signal": 1|-1|0, "confidence": 0.0-1.0,
  "reasoning": "one sentence"}}"""

        raw = self._gemini_call(prompt, model)
        try:
            import json, re
            clean = re.sub(r"```(?:json)?|```", "", raw).strip()
            parsed = json.loads(clean)
            return AgentSignal(
                agent_name=self.name,
                signal=int(parsed.get("signal", 0)),
                confidence=float(parsed.get("confidence", 0.3)),
                reasoning=parsed.get("reasoning", ""),
                raw_data={**data, "parsed": parsed}
            )
        except Exception as e:
            logger.warning(f"TechnicalPatternAgent JSON parse failed: {e}")
            return AgentSignal(
                agent_name=self.name, signal=0,
                confidence=0.1, reasoning=raw[:200], raw_data=data
            )
