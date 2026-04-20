"""
Lightweight financial sentiment scorer using VADER + finance-domain lexicon.
Dropped FinBERT (~440MB) to fit within Render free tier's 512MB RAM limit.
Accuracy is comparable for short financial headlines at this scale.
"""
from __future__ import annotations

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from src.sentiment.preprocessor import clean_headlines
from loguru import logger

# Finance-domain overrides: words VADER under/over-weights for market context
_FINANCE_LEXICON: dict[str, float] = {
    # Strongly bullish
    "rally": 2.5, "breakout": 2.2, "surge": 2.4, "soar": 2.5, "boom": 2.2,
    "record": 1.8, "beat": 1.6, "outperform": 2.0, "upgrade": 1.9,
    "recovery": 1.7, "rebound": 1.8, "inflow": 1.5, "bullish": 2.5,
    "upside": 1.6, "momentum": 1.4, "growth": 1.5, "profit": 1.6,
    # Strongly bearish
    "crash": -3.0, "plunge": -2.8, "tumble": -2.4, "slump": -2.2,
    "selloff": -2.5, "sell-off": -2.5, "recession": -2.6, "default": -2.5,
    "downgrade": -2.0, "bearish": -2.5, "outflow": -1.8, "loss": -1.6,
    "decline": -1.5, "weakness": -1.6, "volatility": -1.2, "risk": -1.0,
    "concern": -1.3, "uncertainty": -1.4, "inflation": -1.3, "rate hike": -1.5,
    # Neutral overrides (VADER wrongly scores these)
    "market": 0.0, "trade": 0.0, "stock": 0.0, "fund": 0.0, "index": 0.0,
}

_analyzer: SentimentIntensityAnalyzer | None = None


def _get_analyzer() -> SentimentIntensityAnalyzer:
    global _analyzer
    if _analyzer is None:
        logger.info("Initialising VADER sentiment analyser with finance lexicon")
        _analyzer = SentimentIntensityAnalyzer()
        _analyzer.lexicon.update(_FINANCE_LEXICON)
    return _analyzer


LABEL_TO_SCORE = {"positive": 1.0, "negative": -1.0, "neutral": 0.0}


def _compound_to_label(compound: float) -> str:
    if compound >= 0.05:
        return "positive"
    if compound <= -0.05:
        return "negative"
    return "neutral"


def score_headlines(headlines: list[str]) -> list[dict]:
    """Score a list of headlines. Returns list of result dicts."""
    if not headlines:
        return []
    cleaned = clean_headlines(headlines)
    analyzer = _get_analyzer()
    results = []
    for original, text in zip(headlines, cleaned):
        scores = analyzer.polarity_scores(text)
        compound = scores["compound"]
        label = _compound_to_label(compound)
        results.append({
            "headline": original,
            "label": label,
            "score": compound,
            "confidence": abs(compound),
        })
    return results
