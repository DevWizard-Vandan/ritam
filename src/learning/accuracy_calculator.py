from loguru import logger
from src.data.db import get_connection

def compute_agent_accuracy(
    agent_name: str,
    window_days: int = 7
) -> dict:
    """
    Computes accuracy for a single agent over the last N days.

    A prediction is attributed to an agent if:
      - agent_signals JSON column contains an entry with
        agent_name == agent_name AND signal != 0
      - prediction is resolved (resolved=1)
      - The agent's directional call matches outcome_correct

    Returns:
      {
        "agent_name": str,
        "total": int,
        "correct": int,
        "accuracy": float,   # correct / total, or 0.5 if no data
        "window_days": int
      }
    """
    from datetime import datetime, timedelta, timezone
    import json

    try:
        import pytz
        ist = pytz.timezone("Asia/Kolkata")
        now = datetime.now(ist)
    except ImportError:
        ist = timezone(timedelta(hours=5, minutes=30))
        now = datetime.now(ist)

    since = (now - timedelta(days=window_days)).isoformat()

    with get_connection() as conn:
        rows = conn.execute("""
            SELECT p.agent_signals, f.actual_return_pct
            FROM predictions p
            JOIN feedback_predictions f ON p.timestamp = f.timestamp
            WHERE f.resolved = 1
              AND p.timestamp >= ?
        """, (since,)).fetchall()

    total = 0
    correct = 0

    for row in rows:
        signals_json, actual_return_pct = row
        if not signals_json:
            continue
        try:
            signals = json.loads(signals_json)
        except (json.JSONDecodeError, TypeError):
            continue

        agent_signal = next(
            (s for s in signals
             if s.get("agent_name") == agent_name
             and s.get("signal", 0) != 0),
            None
        )
        if agent_signal is None:
            continue  # agent abstained — don't count

        total += 1
        # Agent is "correct" if its direction matched the outcome
        predicted_direction = 1 if agent_signal["signal"] > 0 else -1

        if actual_return_pct is None:
            continue

        actual_positive = float(actual_return_pct) > 0

        if predicted_direction == 1 and actual_positive:
            correct += 1
        elif predicted_direction == -1 and not actual_positive:
            correct += 1

    accuracy = (correct / total) if total > 0 else 0.50  # prior = 50%

    return {
        "agent_name": agent_name,
        "total": total,
        "correct": correct,
        "accuracy": round(accuracy, 4),
        "window_days": window_days,
    }


def compute_all_accuracies(window_days: int = 7) -> list[dict]:
    """Computes accuracy for every registered agent."""
    from src.agents.registry import REGISTERED_AGENTS
    from src.agents.macro_synthesis import MacroSynthesisAgent

    results = []
    for cls in REGISTERED_AGENTS:
        if cls is MacroSynthesisAgent:
            continue  # synthesis doesn't get a weight

        name = getattr(cls, 'name', cls.__name__)
        stats = compute_agent_accuracy(name, window_days)
        results.append(stats)

    return results
