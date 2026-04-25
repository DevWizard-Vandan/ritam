from src.trading.performance_tracker import PerformanceTracker


def test_empty_tracker_returns_zero_metrics(tmp_path):
    tracker = PerformanceTracker(db_path=str(tmp_path / "perf.db"), starting_equity=100000)

    metrics = tracker.calculate_metrics()

    assert metrics["total_trades"] == 0
    assert metrics["win_rate"] == 0.0
    assert metrics["expectancy"] == 0.0
    assert metrics["max_drawdown"] == 0.0


def test_record_trade_updates_equity_and_metrics(tmp_path):
    tracker = PerformanceTracker(db_path=str(tmp_path / "perf.db"), starting_equity=100000)
    tracker.record_trade(500, trade_id="t1", signal="BUY_CALL", confidence=0.72, regime="trending_up", timestamp="2026-04-25T10:00:00+05:30")
    tracker.record_trade(-200, trade_id="t2", signal="BUY_PUT", confidence=0.68, regime="trending_down", timestamp="2026-04-25T10:30:00+05:30")

    metrics = tracker.calculate_metrics()

    assert metrics["total_trades"] == 2
    assert metrics["win_rate"] == 0.5
    assert metrics["avg_win"] == 500.0
    assert metrics["avg_loss"] == 200.0
    assert metrics["expectancy"] == 150.0
    assert metrics["ending_equity"] == 100300.0
    assert metrics["daily"]["2026-04-25"]["trades"] == 2


def test_max_drawdown_is_computed_from_equity_curve(tmp_path):
    tracker = PerformanceTracker(db_path=str(tmp_path / "perf.db"), starting_equity=100000)
    tracker.record_trade(1000, trade_id="t1", timestamp="2026-04-25T10:00:00+05:30")
    tracker.record_trade(-3000, trade_id="t2", timestamp="2026-04-25T10:30:00+05:30")
    tracker.record_trade(500, trade_id="t3", timestamp="2026-04-25T11:00:00+05:30")

    metrics = tracker.calculate_metrics()

    assert metrics["equity_curve"] == [100000.0, 101000.0, 98000.0, 98500.0]
    assert round(metrics["max_drawdown"], 4) == 0.0297


def test_daily_breakdown_groups_trades_by_trade_date(tmp_path):
    tracker = PerformanceTracker(db_path=str(tmp_path / "perf.db"), starting_equity=100000)
    tracker.record_trade(250, trade_id="t1", timestamp="2026-04-25T10:00:00+05:30")
    tracker.record_trade(-100, trade_id="t2", timestamp="2026-04-25T12:00:00+05:30")
    tracker.record_trade(400, trade_id="t3", timestamp="2026-04-26T10:00:00+05:30")

    metrics = tracker.calculate_metrics()

    assert metrics["daily"]["2026-04-25"]["trades"] == 2
    assert metrics["daily"]["2026-04-26"]["trades"] == 1
    assert metrics["daily"]["2026-04-25"]["pnl"] == 150.0


def test_record_decision_logs_no_trade_events(tmp_path):
    tracker = PerformanceTracker(db_path=str(tmp_path / "perf.db"), starting_equity=100000)
    tracker.record_decision(
        decision="NO_TRADE",
        reason="PCR_EXTREME",
        trade_id="g1",
        signal=None,
        confidence=0.7,
        regime="trending_up",
        timestamp="2026-04-25T10:15:00+05:30",
    )

    metrics = tracker.calculate_metrics()

    assert metrics["no_trade_events"] == 1
    assert metrics["total_trades"] == 0


def test_record_decision_sampling_controls_log_volume(tmp_path):
    tracker = PerformanceTracker(db_path=str(tmp_path / "perf.db"), starting_equity=100000)
    first = tracker.record_decision(
        decision="NO_TRADE",
        reason="PCR_EXTREME",
        timestamp="2026-04-25T10:15:00+05:30",
        sample_every=3,
    )
    second = tracker.record_decision(
        decision="NO_TRADE",
        reason="PCR_EXTREME",
        timestamp="2026-04-25T10:20:00+05:30",
        sample_every=3,
    )
    third = tracker.record_decision(
        decision="NO_TRADE",
        reason="PCR_EXTREME",
        timestamp="2026-04-25T10:25:00+05:30",
        sample_every=3,
    )

    assert first["should_log"] is True
    assert second["should_log"] is False
    assert third["should_log"] is True


def test_tracker_persists_history_across_instances(tmp_path):
    db_path = str(tmp_path / "perf.db")
    tracker1 = PerformanceTracker(db_path=db_path, starting_equity=100000)
    tracker1.record_trade(300, trade_id="t1", timestamp="2026-04-25T10:00:00+05:30")

    tracker2 = PerformanceTracker(db_path=db_path, starting_equity=100000)
    metrics = tracker2.calculate_metrics()

    assert metrics["total_trades"] == 1
    assert metrics["ending_equity"] == 100300.0
