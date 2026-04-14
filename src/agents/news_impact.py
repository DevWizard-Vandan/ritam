from src.agents.base import AgentBase, AgentSignal
from loguru import logger

class NewsImpactAgent(AgentBase):
    name = "NewsImpactAgent"
    # assigned_api_key set from settings.GEMINI_API_KEY_5 at runtime

    def collect(self) -> dict:
        """Gets headlines from the existing news fetcher."""
        from src.data.news_fetcher import fetch_headlines
        from src.sentiment.scorer import score_headlines
        headlines = fetch_headlines()
        scored = score_headlines(headlines[:20])  # list of dicts with 'score' key
        avg_sentiment = (
            sum(r.get("score", 0.0) for r in scored) / len(scored) if scored else 0.0
        )
        return {
            "headlines": headlines[:20],
            "sentiment_score": avg_sentiment,
        }

    def reason(self, data: dict) -> AgentSignal:
        from src.config import settings
        headlines = data.get("headlines", [])
        sentiment = data.get("sentiment_score", 0.0)
        if not headlines:
            return AgentSignal(
                agent_name=self.name, signal=0, confidence=0.0,
                reasoning="No headlines available", raw_data=data
            )

        headlines_text = "\n".join(f"- {h}" for h in headlines[:15])
        model = (settings.GEMINI_PRO_MODEL if settings.GEMINI_USE_PRO
                 else settings.GEMINI_FLASH_LITE_MODEL)
        prompt = f"""You are a market analyst. FinBERT sentiment score: {sentiment:.4f}
(-1 = very negative, +1 = very positive).

News headlines:
{headlines_text}

Which headlines will most impact Nifty 50 TODAY?
Identify the top market-moving theme and assess directional impact.

Respond ONLY with valid JSON, no markdown:
{{"top_theme": "brief description", "impact": "bullish|bearish|neutral",
  "key_headline": "most impactful headline",
  "signal": 1|-1|0, "confidence": 0.0-1.0,
  "reasoning": "one sentence explaining why"}}"""

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
            logger.warning(f"NewsImpactAgent JSON parse failed: {e}")
            return AgentSignal(
                agent_name=self.name, signal=0,
                confidence=0.1, reasoning=raw[:200], raw_data=data
            )
