import json
import pytest
from src.feedback.tracker import PredictionTracker
from src.learning.weight_updater import WeightUpdater

@pytest.fixture
def tmp_db_path(tmp_path):
    return str(tmp_path / "test_market.db")

@pytest.fixture
def tmp_weights_path(tmp_path):
    path = tmp_path / "agent_weights.json"
    initial_data = {
        "updated_at": "2026-04-05T00:00:00+05:30",
        "weights": {
            "buy": 1.0,
            "sell": 1.0,
            "hold": 1.0
        },
        "week_accuracy": None
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(initial_data, f)
    return str(path)

@pytest.fixture
def tracker(tmp_db_path):
    return PredictionTracker(tmp_db_path)

@pytest.fixture
def updater(tracker, tmp_weights_path):
    return WeightUpdater(tracker, tmp_weights_path)

def test_update_weights_skipped_when_total_less_than_10(updater, tracker):
    # Add 9 correct records for "buy"
    for i in range(9):
        tracker.record_prediction(f"t{i}", "buy", 0.5, "regime", 0.8)
        tracker.record_outcome(f"t{i}", 1.0) # correct

    updated_info = updater.update_weights()
    assert "buy" not in updated_info

    weights = updater.get_current_weights()["weights"]
    assert weights["buy"] == 1.0
    assert weights["sell"] == 1.0
    assert weights["hold"] == 1.0

def test_update_weights_increase_when_accuracy_above_065(updater, tracker):
    # Add 10 records for "buy", 7 correct -> 70% accuracy
    for i in range(10):
        tracker.record_prediction(f"t{i}", "buy", 0.5, "regime", 0.8)
        tracker.record_outcome(f"t{i}", 1.0 if i < 7 else -1.0)

    updated_info = updater.update_weights()
    assert "buy" in updated_info
    assert updated_info["buy"]["accuracy_pct"] == 0.7
    assert updated_info["buy"]["old_weight"] == 1.0
    assert updated_info["buy"]["new_weight"] == 1.05

    weights = updater.get_current_weights()["weights"]
    assert weights["buy"] == 1.05

def test_update_weights_capped_at_2(updater, tracker):
    # Set initial weight close to cap
    current = updater.get_current_weights()
    current["weights"]["sell"] = 1.95
    with open(updater.weights_path, "w") as f:
        json.dump(current, f)

    # 10 records for "sell", all correct -> 100% accuracy
    for i in range(10):
        tracker.record_prediction(f"t{i}", "sell", 0.5, "regime", 0.8)
        tracker.record_outcome(f"t{i}", -1.0)

    updated_info = updater.update_weights()
    assert updated_info["sell"]["new_weight"] == 2.0
    weights = updater.get_current_weights()["weights"]
    assert weights["sell"] == 2.0

def test_update_weights_decrease_when_accuracy_below_045(updater, tracker):
    # 10 records for "hold", 4 correct -> 40% accuracy (actually hold is always correct in _is_correct, so we test "buy")
    # Wait, in the tracker, hold is always correct: return True. So accuracy is always 100%.
    # Let's test "sell" instead.
    for i in range(10):
        tracker.record_prediction(f"t{i}", "sell", 0.5, "regime", 0.8)
        tracker.record_outcome(f"t{i}", -1.0 if i < 4 else 1.0)

    updated_info = updater.update_weights()
    assert "sell" in updated_info
    assert updated_info["sell"]["accuracy_pct"] == 0.4
    assert updated_info["sell"]["old_weight"] == 1.0
    assert updated_info["sell"]["new_weight"] == 0.95

    weights = updater.get_current_weights()["weights"]
    assert weights["sell"] == 0.95

def test_update_weights_floored_at_01(updater, tracker):
    current = updater.get_current_weights()
    current["weights"]["buy"] = 0.105
    with open(updater.weights_path, "w") as f:
        json.dump(current, f)

    for i in range(10):
        tracker.record_prediction(f"t{i}", "buy", 0.5, "regime", 0.8)
        tracker.record_outcome(f"t{i}", -1.0) # all wrong -> 0% accuracy

    updated_info = updater.update_weights()
    assert updated_info["buy"]["new_weight"] == 0.1
    weights = updater.get_current_weights()["weights"]
    assert weights["buy"] == 0.1

def test_update_weights_no_change_when_accuracy_in_range(updater, tracker):
    # 10 records for "buy", 5 correct -> 50% accuracy
    for i in range(10):
        tracker.record_prediction(f"t{i}", "buy", 0.5, "regime", 0.8)
        tracker.record_outcome(f"t{i}", 1.0 if i < 5 else -1.0)

    updated_info = updater.update_weights()
    assert "buy" in updated_info
    assert updated_info["buy"]["new_weight"] == 1.0

    weights = updater.get_current_weights()["weights"]
    assert weights["buy"] == 1.0

def test_empty_db_returns_empty(updater):
    assert updater.update_weights() == {}

def test_get_current_weights_missing_file_returns_defaults(tmp_path, tracker):
    missing_path = tmp_path / "missing.json"
    updater = WeightUpdater(tracker, str(missing_path))
    data = updater.get_current_weights()
    assert data["updated_at"] is None
    assert data["weights"] == {}
    assert data["week_accuracy"] is None
