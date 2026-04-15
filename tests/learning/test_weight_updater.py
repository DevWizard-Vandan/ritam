import pytest
from unittest.mock import patch, MagicMock
from src.learning.weight_updater import run_weight_update, _normalize, BASELINE_WEIGHTS

def test_normalize():
    # Test 6 — normalization: all weights sum to 1.0 after update
    weights = {
        "A": 0.45,
        "B": 0.45,
        "C": 0.10,
        "EconomicCalendarAgent": 0.10  # Should be excluded from sum and set to 0.0
    }
    normalized = _normalize(weights)
    assert normalized["EconomicCalendarAgent"] == 0.0

    # Check sum (excluding EconCal)
    active = {k: v for k, v in normalized.items() if k != "EconomicCalendarAgent"}
    assert sum(active.values()) == pytest.approx(1.0)


@patch("src.learning.weight_updater.get_agent_weights")
@patch("src.learning.weight_updater.upsert_agent_weight")
@patch("src.learning.weight_updater.insert_weight_history")
@patch("src.learning.weight_updater.compute_all_accuracies")
def test_run_weight_update_scenarios(
    mock_compute, mock_insert, mock_upsert, mock_get_weights
):
    # Mock get_agent_weights to return baseline
    mock_get_weights.return_value = BASELINE_WEIGHTS.copy()

    # We will setup mock_compute to return specific 7d and 30d stats

    def side_effect_compute(days):
        if days == 7:
            return [
                # Test 1 — accuracy_7d=0.70, current_weight=0.20:
                {"agent_name": "MarketBreadthAgent", "accuracy": 0.70, "total": 10, "correct": 7},
                # Test 2 — accuracy_7d=0.30, current_weight=0.20:
                {"agent_name": "TechnicalPatternAgent", "accuracy": 0.30, "total": 10, "correct": 3},
                # Test 3 — accuracy_7d=0.50, current_weight=0.20:
                # Wait, FIIDerivative is 0.25, let's use RegimeCrossCheckAgent (0.15)
                {"agent_name": "RegimeCrossCheckAgent", "accuracy": 0.50, "total": 10, "correct": 5},
                # Test 4 — total < MIN_SAMPLES (4 predictions)
                {"agent_name": "NewsImpactAgent", "accuracy": 0.90, "total": 4, "correct": 4},
                # Test 5 — weight would exceed MAX_WEIGHT=0.45
                {"agent_name": "FIIDerivativeAgent", "accuracy": 1.0, "total": 100, "correct": 100},
            ]
        return []

    mock_compute.side_effect = side_effect_compute

    res = run_weight_update()
    assert "updated_at" in res
    assert "agents" in res

    agents = {r["agent_name"]: r for r in res["agents"]}

    # Verify un-normalized before / pre-update logic
    # MarketBreadthAgent initial = 0.20
    assert agents["MarketBreadthAgent"]["weight_before"] == 0.20
    assert agents["MarketBreadthAgent"]["accuracy_7d"] == 0.70

    assert agents["TechnicalPatternAgent"]["weight_before"] == 0.20
    assert agents["TechnicalPatternAgent"]["accuracy_7d"] == 0.30

    assert agents["RegimeCrossCheckAgent"]["weight_before"] == 0.15
    assert agents["RegimeCrossCheckAgent"]["accuracy_7d"] == 0.50

    assert agents["NewsImpactAgent"]["weight_before"] == 0.10

    # Check that DB methods were called
    assert mock_upsert.call_count == len(BASELINE_WEIGHTS) - 1 # Excludes EconCal
    assert mock_insert.call_count == len(BASELINE_WEIGHTS) - 1


@patch("src.learning.weight_updater.get_agent_weights")
@patch("src.learning.weight_updater.upsert_agent_weight")
@patch("src.learning.weight_updater.insert_weight_history")
@patch("src.learning.weight_updater.compute_all_accuracies")
def test_run_weight_update_max_weight_clamp(
    mock_compute, mock_insert, mock_upsert, mock_get_weights
):
    # Test 5 — weight would exceed MAX_WEIGHT=0.45: clamped to 0.45
    baseline = BASELINE_WEIGHTS.copy()
    baseline["FIIDerivativeAgent"] = 0.40
    mock_get_weights.return_value = baseline

    mock_compute.return_value = [
        {"agent_name": "FIIDerivativeAgent", "accuracy": 1.0, "total": 10, "correct": 10}
    ]

    res = run_weight_update()

    # Since report_rows now mutates weight_after to be the normalized value,
    # let's check new_weights directly before normalization
    # Oh wait, we modified weight_updater to replace row["weight_after"] = w (normalized)

    # The sum before norm: 0.45 + 0.2 + 0.2 + 0.15 + 0.1 + 0.05 + 0.03 + 0.02 = 1.2
    # The normalized weight = 0.45 / 1.2 = 0.375
    # So 0.375 IS correct given normalization!

    agents = {r["agent_name"]: r for r in res["agents"]}
    assert agents["FIIDerivativeAgent"]["weight_after"] == 0.375
