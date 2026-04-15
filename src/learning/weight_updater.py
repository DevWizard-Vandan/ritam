"""
RL Weight Updater — runs every Sunday at 00:00 IST.
Reads last 7 days of resolved predictions, computes per-agent
accuracy, updates weights in DB and in _weighted_fallback WEIGHTS.
"""
from loguru import logger
from src.data.db import (
    upsert_agent_weight, insert_weight_history, get_agent_weights
)
from src.learning.accuracy_calculator import (
    compute_agent_accuracy, compute_all_accuracies
)

# ── Hardcoded baseline weights (from _weighted_fallback) ──────────
BASELINE_WEIGHTS = {
    "FIIDerivativeAgent":    0.25,
    "MarketBreadthAgent":    0.20,
    "TechnicalPatternAgent": 0.20,
    "RegimeCrossCheckAgent": 0.15,
    "NewsImpactAgent":       0.10,
    "OptionsChainAgent":     0.05,
    "SectorRotationAgent":   0.03,
    "GlobalMarketAgent":     0.02,
    "EconomicCalendarAgent": 0.00,
}

# ── RL hyperparameters ────────────────────────────────────────────
LEARNING_RATE = 0.15       # how fast weights shift toward accuracy
MIN_WEIGHT    = 0.01       # floor — no agent fully silenced
MAX_WEIGHT    = 0.45       # ceiling — no agent dominates alone
MIN_SAMPLES   = 5          # minimum predictions before weight moves


def _normalize(weights: dict[str, float]) -> dict[str, float]:
    """Re-normalize weights to sum to 1.0 (excluding EconCal)."""
    active = {k: v for k, v in weights.items() if k != "EconomicCalendarAgent"}
    total = sum(active.values())
    if total == 0:
        return weights
    normalized = {k: round(v / total, 4) for k, v in active.items()}
    if "EconomicCalendarAgent" in weights:
        normalized["EconomicCalendarAgent"] = 0.00
    return normalized


def run_weight_update() -> dict:
    """
    Main entry point. Called by scheduler every Sunday.

    Algorithm:
      For each agent:
        1. Compute accuracy_7d and accuracy_30d
        2. If total_7d < MIN_SAMPLES: keep current weight (not enough data)
        3. New weight = current_weight + LEARNING_RATE * (accuracy_7d - 0.5)
           Logic: accuracy > 0.5 → weight increases
                  accuracy < 0.5 → weight decreases
                  accuracy = 0.5 → weight unchanged (random = no info)
        4. Clamp to [MIN_WEIGHT, MAX_WEIGHT]
        5. Normalize all weights to sum to 1.0

    Returns summary dict with before/after weights and accuracy stats.
    """
    from datetime import datetime, timedelta, timezone

    try:
        import pytz
        ist = pytz.timezone("Asia/Kolkata")
        now = datetime.now(ist).isoformat()
    except ImportError:
        ist = timezone(timedelta(hours=5, minutes=30))
        now = datetime.now(ist).isoformat()

    logger.info("Running weekly RL weight update...")

    # Load current weights from DB (or baseline if first run)
    db_weights = get_agent_weights()
    current_weights = {
        k: db_weights.get(k, v)
        for k, v in BASELINE_WEIGHTS.items()
    }

    stats_7d  = {s["agent_name"]: s for s in compute_all_accuracies(7)}
    stats_30d = {s["agent_name"]: s for s in compute_all_accuracies(30)}

    new_weights = {}
    report_rows = []

    for agent_name, current_w in current_weights.items():
        if agent_name == "EconomicCalendarAgent":
            new_weights[agent_name] = 0.00
            continue

        s7  = stats_7d.get(agent_name,  {"accuracy": 0.5, "total": 0, "correct": 0})
        s30 = stats_30d.get(agent_name, {"accuracy": 0.5, "total": 0})

        if s7["total"] < MIN_SAMPLES:
            # Not enough data — hold current weight
            new_w = current_w
            reason = f"insufficient data ({s7['total']} samples)"
        else:
            # RL update: shift toward accuracy signal
            delta = LEARNING_RATE * (s7["accuracy"] - 0.50)
            new_w = current_w + delta
            new_w = max(MIN_WEIGHT, min(MAX_WEIGHT, new_w))
            reason = (f"acc_7d={s7['accuracy']:.3f} "
                      f"delta={delta:+.4f}")

        new_weights[agent_name] = round(new_w, 4)
        report_rows.append({
            "agent_name":  agent_name,
            "weight_before": current_w,
            "weight_after":  round(new_w, 4),
            "accuracy_7d":   s7["accuracy"],
            "accuracy_30d":  s30["accuracy"],
            "total_7d":      s7["total"],
            "correct_7d":    s7["correct"],
            "reason":        reason,
        })

    # Normalize
    new_weights = _normalize(new_weights)

    # Persist to DB
    for row in report_rows:
        agent = row["agent_name"]
        w = new_weights.get(agent, row["weight_after"])
        row["weight_after"] = w
        upsert_agent_weight(
            agent_name=agent,
            weight=w,
            accuracy_7d=row["accuracy_7d"],
            accuracy_30d=row["accuracy_30d"],
            total=row["total_7d"],
            correct=row["correct_7d"],
        )
        insert_weight_history(agent, w, row["accuracy_7d"])

    # Log the report
    logger.info("═══ RL Weight Update Report ═══")
    for row in sorted(report_rows, key=lambda r: -r["weight_after"]):
        arrow = "↑" if row["weight_after"] > row["weight_before"] else (
                "↓" if row["weight_after"] < row["weight_before"] else "→")
        logger.info(
            f"  {row['agent_name']:28s} "
            f"{row['weight_before']:.4f} {arrow} {row['weight_after']:.4f} "
            f"| acc_7d={row['accuracy_7d']:.3f} "
            f"| n={row['total_7d']}"
        )
    logger.info("═══════════════════════════════")

    return {
        "updated_at": now,
        "agents": report_rows,
        "new_weights": new_weights,
    }
