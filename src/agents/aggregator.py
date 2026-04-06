"""
Master Signal Aggregator — combines all agent signals into one prediction.
Reads weights from config/agent_weights.json.
Output format follows ADR-005 in DECISIONS.md.
"""
import json
import os
from datetime import datetime
import pytz
from src.config import settings

WEIGHTS_PATH = "config/agent_weights.json"
DEFAULT_WEIGHTS = {
    "sentiment_agent": 0.25,
    "gift_nifty_agent": 0.25,
    "macro_agent": 0.25,
    "volatility_agent": 0.25
}
IST = pytz.timezone(settings.TIMEZONE)


def load_weights() -> dict:
    if os.path.exists(WEIGHTS_PATH):
        with open(WEIGHTS_PATH) as f:
            return json.load(f).get("weights", DEFAULT_WEIGHTS)
    return DEFAULT_WEIGHTS


def aggregate(signals: dict) -> dict:
    """
    signals: {
      "sentiment_agent":  {"direction": "up", "strength": 0.7, "confidence": 0.8},
      "gift_nifty_agent": {"direction": "up", "strength": 0.5, "confidence": 0.9},
      "macro_agent":      {"direction": "neutral", "strength": 0.2, "confidence": 0.6},
      "volatility_agent": {"direction": "down", "strength": 0.3, "confidence": 0.7}
    }
    """
    weights = load_weights()
    direction_score = 0.0
    total_weight = 0.0
    for agent, signal in signals.items():
        w = weights.get(agent, 0.25)
        d_val = {"up": 1.0, "down": -1.0, "neutral": 0.0}.get(signal["direction"], 0.0)
        direction_score += w * d_val * signal["strength"] * signal["confidence"]
        total_weight += w
    if total_weight > 0:
        direction_score /= total_weight
    direction = "up" if direction_score > 0.1 else "down" if direction_score < -0.1 else "neutral"
    predicted_pct = round(abs(direction_score) * 1.5, 3)  # rough magnitude estimate
    confidence = round(min(abs(direction_score) * 1.2, 1.0), 3)
    return {
        "timestamp": datetime.now(IST).isoformat(),
        "predicted_direction": direction,
        "predicted_move_pct": predicted_pct,
        "confidence": confidence,
        "timeframe_minutes": 20,
        "signals_used": list(signals.keys()),
        "regime": "unknown"
    }
