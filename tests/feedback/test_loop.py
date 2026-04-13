import pytest
from unittest.mock import patch
from datetime import datetime, timezone, timedelta
from src.feedback.loop import FeedbackLoop
from src.feedback.tracker import PredictionTracker
from src.orchestrator.agent import OrchestratorResult

@pytest.fixture
def temp_tracker(tmp_path):
    db_path = tmp_path / "test_loop.db"
    return PredictionTracker(str(db_path))

@pytest.fixture
def feedback_loop(temp_tracker):
    return FeedbackLoop(temp_tracker)

def test_record_prediction_stores_correct_fields(feedback_loop, temp_tracker):
    result = OrchestratorResult(
        regime="trending_up",
        sentiment_score=0.8,
        top_analogs=[{"similarity_score": 0.95}],
        signal="buy"
    )

    timestamp = feedback_loop.record_prediction(result)

    # Assert timestamp was returned
    assert timestamp is not None
    assert "T" in timestamp

    # Assert the prediction was saved in the tracker's database
    with temp_tracker._connect() as conn:
        row = conn.execute("SELECT timestamp, signal, sentiment_score, regime, analog_similarity FROM feedback_predictions WHERE timestamp = ?", (timestamp,)).fetchone()

    assert row is not None
    assert row[0] == timestamp
    assert row[1] == "buy"
    assert row[2] == 0.8
    assert row[3] == "trending_up"
    assert row[4] == 0.95

@patch("src.feedback.loop.read_candles")
def test_resolve_outcome_calculates_return_pct_correctly(mock_read_candles, feedback_loop, temp_tracker):
    timestamp = "2023-10-25T10:00:00+05:30"

    # Pre-populate prediction
    temp_tracker.record_prediction(timestamp, "buy", 0.8, "trending_up", 0.95)

    mock_read_candles.return_value = [
        {"close": 100.0},
        {"close": 105.0}
    ]

    result = feedback_loop.resolve_outcome(timestamp)

    assert result is not None
    assert result["timestamp"] == timestamp
    assert result["actual_return_pct"] == 5.0  # (105 - 100) / 100 * 100

    # Check if DB was updated
    with temp_tracker._connect() as conn:
        row = conn.execute("SELECT actual_return_pct, resolved FROM feedback_predictions WHERE timestamp = ?", (timestamp,)).fetchone()

    assert row is not None
    assert row[0] == 5.0
    assert row[1] == 1

@patch("src.feedback.loop.read_candles")
def test_resolve_outcome_returns_none_when_candles_missing(mock_read_candles, feedback_loop):
    timestamp = "2023-10-25T10:00:00+05:30"

    # Mock returns less than 2 candles
    mock_read_candles.return_value = [{"close": 100.0}]

    result = feedback_loop.resolve_outcome(timestamp)
    assert result is None

    # Mock returns empty
    mock_read_candles.return_value = []

    result = feedback_loop.resolve_outcome(timestamp)
    assert result is None

@patch("src.feedback.loop.read_candles")
def test_resolve_outcome_returns_none_when_entry_close_is_zero(mock_read_candles, feedback_loop, temp_tracker):
    timestamp = "2023-10-25T10:00:00+05:30"
    temp_tracker.record_prediction(timestamp, "buy", 0.8, "trending_up", 0.95)

    # Mock returns entry close as 0.0
    mock_read_candles.return_value = [{"close": 0.0}, {"close": 105.0}]

    result = feedback_loop.resolve_outcome(timestamp)
    assert result is None

def test_resolve_outcome_invalid_timestamp(feedback_loop):
    result = feedback_loop.resolve_outcome("invalid-timestamp")
    assert result is None
