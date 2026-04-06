"""
Market regime classifier — uses Gemma 4 E2B to classify current regime.
Returns one of: crisis / recovery / trending_up / trending_down / choppy / baseline
"""
from src.reasoning.gemma_client import quick_reason
from loguru import logger

REGIME_PROMPT = """
You are a market analyst. Based on these indicators:
- Last 20 candle price change: {price_change_pct}%
- India VIX: {vix}
- News volume today: {news_count} articles
- Sentiment score: {sentiment}

Classify the current market regime. Reply with EXACTLY one word from this list:
crisis / recovery / trending_up / trending_down / choppy / baseline

Reply with only the single word. No explanation.
"""

VALID_REGIMES = {"crisis", "recovery", "trending_up", "trending_down", "choppy", "baseline"}


def classify_regime(price_change_pct: float, vix: float,
                    news_count: int, sentiment: float) -> str:
    prompt = REGIME_PROMPT.format(
        price_change_pct=round(price_change_pct, 2),
        vix=round(vix, 1),
        news_count=news_count,
        sentiment=round(sentiment, 2)
    )
    result = quick_reason(prompt).strip().lower().rstrip(".")
    if result not in VALID_REGIMES:
        logger.warning(f"Unexpected regime response: '{result}' — defaulting to baseline")
        return "baseline"
    logger.info(f"Regime classified as: {result}")
    return result
