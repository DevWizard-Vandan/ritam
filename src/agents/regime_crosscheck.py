from src.agents.base import AgentBase, AgentSignal
from loguru import logger

class RegimeCrossCheckAgent(AgentBase):
    name = "RegimeCrossCheckAgent"
    # assigned_api_key set from settings.GEMINI_API_KEY_6 at runtime

    def collect(self) -> dict:
        from src.data.db import read_candles
        from datetime import date, timedelta
        to_date = str(date.today())
        from_date = str(date.today() - timedelta(days=90))
        candles = read_candles("NSE:NIFTY 50", from_date, to_date)
        closes = [c["close"] for c in candles[-30:]]
        highs = [c["high"] for c in candles[-30:]]
        lows = [c["low"] for c in candles[-30:]]
        avg = sum(closes) / len(closes) if closes else 0
        volatility = (max(closes) - min(closes)) / avg * 100 if avg else 0
        last = closes[-1] if closes else 0
        ma20 = avg
        ma5 = sum(closes[-5:]) / 5 if len(closes) >= 5 else avg
        return {
            "last_close": last,
            "ma5": round(ma5, 2),
            "ma20": round(ma20, 2),
            "volatility_30d_pct": round(volatility, 2),
            "recent_high": max(highs) if highs else 0,
            "recent_low": min(lows) if lows else 0,
        }

    def reason(self, data: dict) -> AgentSignal:
        from src.config import settings
        model = (settings.GEMINI_PRO_MODEL if settings.GEMINI_USE_PRO
                 else settings.GEMINI_FLASH_LITE_MODEL)
        prompt = f"""Market statistics for Nifty 50 (last 30 days):
Last close: {data['last_close']}
MA5: {data['ma5']} | MA20: {data['ma20']}
30-day range: {data['recent_low']} – {data['recent_high']}
Volatility (range/avg): {data['volatility_30d_pct']:.1f}%

Classify the current market regime:
- trending_up: clear uptrend, price above both MAs
- trending_down: clear downtrend, price below both MAs
- choppy: oscillating, no clear trend
- breakout: approaching key resistance with momentum
- crisis: sharp sell-off, volatility > 8%

Respond ONLY with valid JSON, no markdown:
{{"regime": "trending_up|trending_down|choppy|breakout|crisis",
  "confidence": 0.0-1.0,
  "reasoning": "one sentence",
  "signal": 1|-1|0}}"""

        raw = self._gemini_call(prompt, model)
        try:
            import json, re
            clean = re.sub(r"```(?:json)?|```", "", raw).strip()
            parsed = json.loads(clean)
            return AgentSignal(
                agent_name=self.name,
                signal=int(parsed.get("signal", 0)),
                confidence=float(parsed.get("confidence", 0.4)),
                reasoning=f"Regime={parsed.get('regime')}: "
                          f"{parsed.get('reasoning','')}",
                raw_data={**data, "parsed": parsed}
            )
        except Exception as e:
            logger.warning(f"RegimeCrossCheckAgent parse failed: {e}")
            return AgentSignal(
                agent_name=self.name, signal=0,
                confidence=0.1, reasoning=raw[:200], raw_data=data
            )
