from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.data.db import read_daily_metrics
from src.trading.evaluation_mode import (
    EvaluationSafetyGuard,
    ensure_evaluation_state,
    export_trade_log,
    generate_daily_summary,
    get_system_metrics,
    validate_system_ready,
)
from src.trading.performance_tracker import PerformanceTracker


IST = timezone(timedelta(hours=5, minutes=30))


def _seed_tracker(db_path: str) -> PerformanceTracker:
    tracker = PerformanceTracker(db_path=db_path, starting_equity=100000)
    tracker.record_trade(
        500,
        trade_id="t1",
        signal="BUY_CALL",
        confidence=0.72,
        regime="trending_up",
        timestamp="2026-04-25T10:00:00+05:30",
        pcr_value=1.05,
        reason_code="TRADE_ALLOWED",
    )
    tracker.record_decision(
        decision="NO_TRADE",
        reason="PCR_EXTREME",
        trade_id="n1",
        signal="BUY_PUT",
        confidence=0.61,
        regime="trending_down",
        timestamp="2026-04-25T10:15:00+05:30",
        pcr_value=1.7,
    )
    tracker.record_decision(
        decision="NO_TRADE",
        reason="LOW_EFFECTIVE_CONFIDENCE",
        trade_id="n2",
        signal="BUY_CALL",
        confidence=0.63,
        regime="trending_up",
        timestamp="2026-04-25T11:00:00+05:30",
        pcr_value=1.0,
    )
    tracker.record_trade(
        -200,
        trade_id="t2",
        signal="BUY_PUT",
        confidence=0.69,
        regime="trending_down",
        timestamp="2026-04-26T10:00:00+05:30",
        pcr_value=0.95,
        reason_code="TRADE_ALLOWED",
    )
    return tracker


def test_get_system_metrics_includes_no_trade_breakdown(tmp_path):
    db_path = str(tmp_path / "metrics.db")
    tracker = _seed_tracker(db_path)

    metrics = get_system_metrics(db_path=db_path)

    assert metrics["total_trades"] == 2
    assert metrics["trades_today"] == 1
    assert metrics["no_trade_count_today"] == 2
    assert metrics["no_trade_counts_today"]["PCR_EXTREME"] == 1
    assert metrics["no_trade_counts_today"]["LOW_EFFECTIVE_CONFIDENCE"] == 1
    assert metrics["current_equity"] == tracker.calculate_metrics()["ending_equity"]
    assert metrics["no_tweak_mode"] is True


def test_generate_daily_summary_persists_daily_metrics(tmp_path):
    db_path = str(tmp_path / "summary.db")
    _seed_tracker(db_path)

    summary = generate_daily_summary("2026-04-25", db_path=db_path)
    rows = read_daily_metrics(limit=10, db_path=db_path)

    assert summary["date"] == "2026-04-25"
    assert summary["trades"] == 1
    assert summary["top_reason_for_no_trade"] == "PCR_EXTREME"
    assert rows[0]["metric_date"] == "2026-04-25"
    assert rows[0]["trades"] == 1


def test_export_trade_log_returns_required_fields(tmp_path):
    db_path = str(tmp_path / "export.db")
    _seed_tracker(db_path)

    journal = export_trade_log(db_path=db_path)

    assert len(journal) == 4
    first = journal[0]
    assert first["trade_id"] == "t1"
    assert first["timestamp"] == "2026-04-25T10:00:00+05:30"
    assert first["signal"] == "CALL"
    assert first["confidence"] == 0.72
    assert first["regime"] == "trending_up"
    assert first["pcr_value"] == 1.05
    assert first["decision"] == "TRADE"
    assert first["profit_loss"] == 500.0
    assert first["equity_after"] == 100500.0


def test_evaluation_guard_warns_on_trade_soft_limit(tmp_path):
    db_path = str(tmp_path / "guard.db")
    tracker = PerformanceTracker(db_path=db_path, starting_equity=100000)
    tracker.record_trade(100, trade_id="t1", timestamp="2026-04-25T10:00:00+05:30")
    tracker.record_trade(100, trade_id="t2", timestamp="2026-04-25T11:00:00+05:30")
    tracker.record_trade(100, trade_id="t3", timestamp="2026-04-25T12:00:00+05:30")

    guard = EvaluationSafetyGuard(db_path=db_path)
    safety = guard.evaluate_safety(
        {
            "decision": "TRADE",
            "reason_code": "TRADE_ALLOWED",
            "details": {"pcr_available": True},
        },
        "2026-04-25T12:30:00+05:30",
    )

    assert safety["skip"] is False
    assert safety["warn_trade_limit"] is True
    assert safety["trade_count_today"] == 3


def test_evaluation_guard_blocks_when_pcr_unavailable_too_long(tmp_path):
    db_path = str(tmp_path / "pcr_guard.db")
    guard = EvaluationSafetyGuard(db_path=db_path)

    first = guard.evaluate_safety(
        {
            "decision": "TRADE",
            "reason_code": "TRADE_ALLOWED",
            "details": {"pcr_available": False},
        },
        datetime(2026, 4, 25, 10, 0, tzinfo=IST),
    )
    second = guard.evaluate_safety(
        {
            "decision": "TRADE",
            "reason_code": "TRADE_ALLOWED",
            "details": {"pcr_available": False},
        },
        datetime(2026, 4, 25, 10, 31, tzinfo=IST),
    )

    assert first["skip"] is False
    assert second["skip"] is True
    assert second["reason_code"] == "PCR_UNAVAILABLE_TOO_LONG"


def test_ensure_evaluation_state_creates_first_run_marker(tmp_path):
    db_path = str(tmp_path / "state.db")

    state = ensure_evaluation_state(db_path=db_path)

    assert state["evaluation_start_date"] == "2026-04-25"
    assert state["starting_equity"] == 100000.0


def test_validate_system_ready_returns_ready_with_mocked_pcr(monkeypatch, tmp_path):
    db_path = str(tmp_path / "ready.db")
    _seed_tracker(db_path)

    monkeypatch.setattr(
        "src.trading.evaluation_mode.fetch_nifty_pcr",
        lambda **kwargs: {
            "available": True,
            "status": "ok",
            "pcr": 1.05,
            "is_stale": False,
        },
    )

    class _Scheduler:
        running = True

        def get_jobs(self):
            return [type("Job", (), {"id": "market_cycle"})()]

    report = validate_system_ready(db_path=db_path, scheduler=_Scheduler())

    assert report["status"] == "READY"
    assert report["checks"]["database_connection"]["ok"] is True
    assert report["checks"]["required_tables"]["ok"] is True
    assert report["checks"]["pcr_fetcher"]["ok"] is True
    assert report["checks"]["scheduler"]["ok"] is True
    assert report["checks"]["config"]["ok"] is True
    assert report["checks"]["evaluation_state"]["ok"] is True
