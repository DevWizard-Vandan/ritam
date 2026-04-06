"""
Historical analog finder — uses Gemma 4 26B to find past market scenarios
that most closely resemble current conditions.
"""
from src.reasoning.gemma_client import deep_reason
from loguru import logger


ANALOG_PROMPT_TEMPLATE = """
You are a financial historian with deep knowledge of global market history.

Current market conditions:
- Regime: {regime}
- India VIX level: {vix_level} ({vix_label})
- Sentiment score: {sentiment_score} ({sentiment_label})
- GIFT Nifty overnight gap: {gift_gap_pct}%
- Active macro event: {macro_event}

Task: Find the 3 most historically similar market scenarios.
These can be from any global market (Indian, US, global) and any era.

For each scenario, respond in this EXACT format:
MATCH_1: [scenario name and approximate date]
SIMILARITY: [short description of why conditions match]
OUTCOME: [what the market did over the next 5–10 sessions]
CONFIDENCE: [high/medium/low]

MATCH_2: ...
SIMILARITY: ...
OUTCOME: ...
CONFIDENCE: ...

MATCH_3: ...
SIMILARITY: ...
OUTCOME: ...
CONFIDENCE: ...

Be specific and concise.
"""


def find_analogs(conditions: dict) -> list[dict]:
    """
    conditions = {
      "regime": "recovery",
      "vix_level": 18.5,
      "sentiment_score": 0.62,
      "gift_gap_pct": 0.45,
      "macro_event": "RBI holds rates"
    }
    Returns list of 3 analog dicts.
    """
    vix = conditions.get("vix_level", 0)
    vix_label = "low" if vix < 14 else "high" if vix > 22 else "moderate"
    sentiment = conditions.get("sentiment_score", 0)
    sentiment_label = "bullish" if sentiment > 0.3 else "bearish" if sentiment < -0.3 else "neutral"

    prompt = ANALOG_PROMPT_TEMPLATE.format(
        regime=conditions.get("regime", "unknown"),
        vix_level=vix,
        vix_label=vix_label,
        sentiment_score=round(sentiment, 2),
        sentiment_label=sentiment_label,
        gift_gap_pct=conditions.get("gift_gap_pct", 0.0),
        macro_event=conditions.get("macro_event", "None")
    )

    raw = deep_reason(prompt)
    if raw == "REASONING_UNAVAILABLE":
        return []

    return _parse_analogs(raw)


def _parse_analogs(raw: str) -> list[dict]:
    """Parse Gemma's structured response into a list of dicts."""
    analogs = []
    blocks = raw.strip().split("MATCH_")
    for block in blocks[1:4]:  # max 3
        lines = block.strip().splitlines()
        analog = {"match": "", "similarity_description": "", "expected_outcome": "", "confidence": "medium"}
        for line in lines:
            if line.startswith(("1:", "2:", "3:")):
                analog["match"] = line.split(":", 1)[-1].strip()
            elif line.upper().startswith("SIMILARITY:"):
                analog["similarity_description"] = line.split(":", 1)[-1].strip()
            elif line.upper().startswith("OUTCOME:"):
                analog["expected_outcome"] = line.split(":", 1)[-1].strip()
            elif line.upper().startswith("CONFIDENCE:"):
                analog["confidence"] = line.split(":", 1)[-1].strip().lower()
        if analog["match"]:
            analogs.append(analog)
    return analogs
