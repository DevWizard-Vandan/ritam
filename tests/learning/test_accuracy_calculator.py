import json
import pytest
from datetime import datetime, timedelta, timezone
from src.learning.accuracy_calculator import compute_agent_accuracy, compute_all_accuracies
from src.data.db import get_connection

@pytest.fixture(autouse=True)
def clean_db():
    with get_connection() as conn:
        conn.execute("DELETE FROM predictions")
        conn.execute("DELETE FROM feedback_predictions")
        conn.commit()

def test_compute_agent_accuracy_correct():
    agent_name = "TestAgent"
    now = datetime.now(timezone.utc)

    with get_connection() as conn:
        for i in range(5):
            # Using timedelta with minutes to ensure uniqueness
            ts = (now - timedelta(days=1, minutes=i)).isoformat()
            ret = 1.0 if i < 4 else -1.0
            signals = [{"agent_name": agent_name, "signal": 1}]
            conn.execute("INSERT INTO predictions (timestamp, agent_signals) VALUES (?, ?)", (ts, json.dumps(signals)))
            conn.execute("INSERT INTO feedback_predictions (timestamp, resolved, actual_return_pct) VALUES (?, 1, ?)", (ts, ret))
        conn.commit()

    res = compute_agent_accuracy(agent_name)
    assert res["accuracy"] == 0.80
    assert res["total"] == 5
    assert res["correct"] == 4


def test_compute_agent_accuracy_no_predictions():
    agent_name = "TestAgent"
    res = compute_agent_accuracy(agent_name)
    assert res["accuracy"] == 0.50
    assert res["total"] == 0
    assert res["correct"] == 0


def test_compute_agent_accuracy_abstained():
    agent_name = "TestAgent"
    now = datetime.now(timezone.utc)
    with get_connection() as conn:
        for i in range(3):
            ts = (now - timedelta(days=1, minutes=i)).isoformat()
            signals = [{"agent_name": agent_name, "signal": 0}]
            conn.execute("INSERT INTO predictions (timestamp, agent_signals) VALUES (?, ?)", (ts, json.dumps(signals)))
            conn.execute("INSERT INTO feedback_predictions (timestamp, resolved, actual_return_pct) VALUES (?, 1, 1.0)", (ts,))
        conn.commit()

    res = compute_agent_accuracy(agent_name)
    assert res["accuracy"] == 0.50
    assert res["total"] == 0


def test_compute_agent_accuracy_mixed_window():
    agent_name = "TestAgent"
    now = datetime.now(timezone.utc)
    with get_connection() as conn:
        for i in range(5):
            ts = (now - timedelta(days=1, minutes=i)).isoformat()
            if i in [0, 1]:
                sig, ret = 1, 1.0  # Correct
            elif i == 2:
                sig, ret = -1, -1.0 # Correct
            elif i in [3, 4]:
                sig, ret = 1, -1.0 # Wrong

            signals = [{"agent_name": agent_name, "signal": sig}]
            conn.execute("INSERT INTO predictions (timestamp, agent_signals) VALUES (?, ?)", (ts, json.dumps(signals)))
            conn.execute("INSERT INTO feedback_predictions (timestamp, resolved, actual_return_pct) VALUES (?, 1, ?)", (ts, ret))
        conn.commit()

    res = compute_agent_accuracy(agent_name)
    assert res["accuracy"] == 0.60
    assert res["total"] == 5
    assert res["correct"] == 3


def test_compute_all_accuracies():
    res = compute_all_accuracies()
    agent_names = [r["agent_name"] for r in res]
    assert "MacroSynthesisAgent" not in agent_names
    assert "FIIDerivativeAgent" in agent_names
    for r in res:
        assert "accuracy" in r
