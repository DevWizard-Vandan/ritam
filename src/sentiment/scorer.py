"""
Lightweight financial sentiment scorer using VADER + finance-domain lexicon.
Dropped FinBERT (~440MB) to fit within Render free tier's 512MB RAM limit.
Accuracy is comparable for short financial headlines at this scale.
"""
from __future__ import annotations

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from src.sentiment.preprocessor import clean_headlines
try:
    from loguru import logger
except ModuleNotFoundError:  # pragma: no cover - environment fallback
    import logging

    logger = logging.getLogger(__name__)
import os

MODEL_PATH = "models/finbert"
HF_MODEL_ID = "ProsusAI/finbert"

_pipeline = None


def _load_pipeline():
    global _pipeline
    if _pipeline is not None:
        return _pipeline
    if os.path.exists(MODEL_PATH):
        logger.info("Loading FinBERT from local cache")
        _pipeline = pipeline("text-classification", model=MODEL_PATH,
                             tokenizer=MODEL_PATH, top_k=None)
    else:
        logger.info("Downloading FinBERT from HuggingFace — this may take a few minutes")
        os.makedirs(MODEL_PATH, exist_ok=True)
        tokenizer = AutoTokenizer.from_pretrained(HF_MODEL_ID)
        model = AutoModelForSequenceClassification.from_pretrained(HF_MODEL_ID)
        tokenizer.save_pretrained(MODEL_PATH)
        model.save_pretrained(MODEL_PATH)
        _pipeline = pipeline("text-classification", model=model,
                             tokenizer=tokenizer, top_k=None)
    return _pipeline


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
