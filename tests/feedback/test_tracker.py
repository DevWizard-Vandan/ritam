"""Unit tests for the feedback prediction tracker."""
from src.feedback.tracker import PredictionTracker


def test_record_prediction_stores_correct_fields():
    tracker = PredictionTracker(":memory:")
    tracker.record_prediction(
        timestamp="2026-04-11T09:15:00+05:30",
        signal="buy",
        sentiment_score=0.42,
        regime="recovery",
        analog_similarity=0.73,
    )

    with tracker._connect() as conn:
        row = conn.execute(
            """
            SELECT timestamp, signal, sentiment_score, regime, analog_similarity, resolved
            FROM feedback_predictions
            WHERE timestamp = ?
            """,
            ("2026-04-11T09:15:00+05:30",),
        ).fetchone()

    assert row == ("2026-04-11T09:15:00+05:30", "buy", 0.42, "recovery", 0.73, 0)


def test_record_outcome_resolves_row():
    tracker = PredictionTracker(":memory:")
    timestamp = "2026-04-11T09:20:00+05:30"
    tracker.record_prediction(timestamp, "sell", -0.2, "trending_down", 0.61)

    tracker.record_outcome(timestamp=timestamp, actual_return_pct=-0.35)

    with tracker._connect() as conn:
        row = conn.execute(
            "SELECT actual_return_pct, resolved FROM feedback_predictions WHERE timestamp = ?",
            (timestamp,),
        ).fetchone()

    assert row == (-0.35, 1)


def test_get_accuracy_stats_returns_correct_accuracy_pct():
    tracker = PredictionTracker(":memory:")
    tracker.record_prediction("t1", "buy", 0.3, "recovery", 0.7)
    tracker.record_prediction("t2", "sell", -0.2, "crisis", 0.8)
    tracker.record_outcome("t1", 0.1)
    tracker.record_outcome("t2", 0.25)

    stats = tracker.get_accuracy_stats()

    assert stats["total"] == 2
    assert stats["correct"] == 1
    assert stats["accuracy_pct"] == 0.5


def test_buy_signal_with_positive_return_is_correct():
    tracker = PredictionTracker(":memory:")
    tracker.record_prediction("t_buy", "buy", 0.4, "trending_up", 0.69)
    tracker.record_outcome("t_buy", 0.2)

    stats = tracker.get_accuracy_stats()

    assert stats["correct"] == 1
    assert stats["by_signal"]["buy"]["correct"] == 1


def test_sell_signal_with_negative_return_is_correct():
    tracker = PredictionTracker(":memory:")
    tracker.record_prediction("t_sell", "sell", -0.4, "crisis", 0.71)
    tracker.record_outcome("t_sell", -0.2)

    stats = tracker.get_accuracy_stats()

    assert stats["correct"] == 1
    assert stats["by_signal"]["sell"]["correct"] == 1


def test_stats_return_zero_totals_on_empty_db():
    tracker = PredictionTracker(":memory:")

    stats = tracker.get_accuracy_stats()

    assert stats["total"] == 0
    assert stats["correct"] == 0
    assert stats["accuracy_pct"] == 0.0
    assert stats["avg_error"] == 0.0
