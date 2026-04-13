"""Updates weights based on RL feedback."""
from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timedelta, timezone

from src.feedback.tracker import PredictionTracker


class WeightUpdater:
    def __init__(self, tracker: PredictionTracker, weights_path: str = "config/signal_weights.json"):
        self.tracker = tracker
        self.weights_path = Path(weights_path)

    def get_current_weights(self) -> dict:
        if not self.weights_path.exists():
            return {"updated_at": None, "weights": {}, "week_accuracy": None}
        with open(self.weights_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def update_weights(self) -> dict:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        stats = self.tracker.get_accuracy_stats(since=cutoff)
        by_signal = stats.get("by_signal", {})

        current_data = self.get_current_weights()
        weights = current_data.get("weights", {})

        updated_info = {}

        for signal in ["buy", "sell", "hold"]:
            signal_stats = by_signal.get(signal, {})
            total = signal_stats.get("total", 0)
            accuracy = signal_stats.get("accuracy_pct", 0.0)

            if total < 10:
                continue

            old_weight = weights.get(signal, 1.0)

            if accuracy > 0.65:
                new_weight = min(old_weight * 1.05, 2.0)
            elif accuracy < 0.45:
                new_weight = max(old_weight * 0.95, 0.1)
            else:
                new_weight = old_weight

            new_weight = round(new_weight, 4)
            weights[signal] = new_weight

            updated_info[signal] = {
                "old_weight": old_weight,
                "new_weight": new_weight,
                "accuracy_pct": accuracy
            }

        ist = timezone(timedelta(hours=5, minutes=30))
        current_data["updated_at"] = datetime.now(ist).replace(microsecond=0).isoformat()
        current_data["weights"] = weights
        current_data["week_accuracy"] = stats.get("accuracy_pct")

        self.weights_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.weights_path, "w", encoding="utf-8") as f:
            json.dump(current_data, f, indent=2)

        return updated_info
