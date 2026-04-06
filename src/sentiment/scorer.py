"""
FinBERT-based financial sentiment scorer.
Downloads model once and caches locally in models/finbert/.
"""
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
from src.sentiment.preprocessor import clean_headlines
from loguru import logger
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


def score_headlines(headlines: list[str]) -> list[dict]:
    """Score a list of headlines. Returns list of result dicts."""
    if not headlines:
        return []
    cleaned = clean_headlines(headlines)
    pipe = _load_pipeline()
    results = []
    for headline, raw in zip(headlines, pipe(cleaned, batch_size=16)):
        best = max(raw, key=lambda x: x["score"])
        label = best["label"].lower()
        results.append({
            "headline": headline,
            "label": label,
            "score": LABEL_TO_SCORE.get(label, 0.0) * best["score"],
            "confidence": best["score"]
        })
    return results
