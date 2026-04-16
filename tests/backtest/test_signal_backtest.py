"""Tests for signal backtest engine."""
from __future__ import annotations

import json

from src.backtest.signal_backtest import BacktestResult, SignalBacktester


def _row(ts: str, signal: str, ret: float, agent_signals: list[dict] | None = None) -> dict:
    return {
        "timestamp": ts,
        "signal": signal,
        "actual_return_pct": ret,
        "agent_signals": json.dumps(agent_signals or []),
    }


def test_backtest_returns_correct_shape(monkeypatch):
    rows = [
        _row("2026-01-01T09:15:00+00:00", "buy", 0.8, [{"agent_name": "A", "signal": 1, "confidence": 0.8}]),
        _row("2026-01-01T09:30:00+00:00", "sell", -0.5, [{"agent_name": "A", "signal": -1, "confidence": 0.6}]),
        _row("2026-01-01T09:45:00+00:00", "hold", 0.1, [{"agent_name": "A", "signal": 0, "confidence": 0.9}]),
    ]
    monkeypatch.setattr(SignalBacktester, "_load_rows", lambda *args, **kwargs: rows)

    result = SignalBacktester().run("2026-01-01", "2026-01-07")

    assert isinstance(result, BacktestResult)
    assert result.from_date == "2026-01-01"
    assert result.to_date == "2026-01-07"
    assert "win_rate" in result.rl_weighted
    assert "total_pnl" in result.rl_weighted
    assert "sharpe_ratio" in result.rl_weighted
    assert "max_drawdown" in result.rl_weighted
    assert "equity_curve" in result.rl_weighted
    assert "win_rate" in result.equal_weight
    assert isinstance(result.generated_at, str)


def test_sharpe_positive_for_winning_strategy(monkeypatch):
    rows = [
        _row("2026-01-01T09:15:00+00:00", "buy", 1.1),
        _row("2026-01-02T09:15:00+00:00", "sell", -1.0),
        _row("2026-01-03T09:15:00+00:00", "buy", 0.9),
    ]
    monkeypatch.setattr(SignalBacktester, "_load_rows", lambda *args, **kwargs: rows)

    result = SignalBacktester().run("2026-01-01", "2026-01-03")

    assert result.rl_weighted["win_rate"] == 1.0
    assert result.rl_weighted["sharpe_ratio"] > 0


def test_equal_weight_baseline_always_present(monkeypatch):
    rows = [
        _row("2026-01-01T09:15:00+00:00", "hold", 0.0),
    ]
    monkeypatch.setattr(SignalBacktester, "_load_rows", lambda *args, **kwargs: rows)

    result = SignalBacktester().run("2026-01-01", "2026-01-07")

    assert isinstance(result.equal_weight, dict)
    assert "win_rate" in result.equal_weight
    assert result.equal_weight["total_trades"] == 0


def test_empty_predictions_returns_zero_metrics(monkeypatch):
    monkeypatch.setattr(SignalBacktester, "_load_rows", lambda *args, **kwargs: [])

    result = SignalBacktester().run("2026-01-01", "2026-01-07")

    assert result.total_trades == 0
    assert result.rl_weighted["win_rate"] == 0.0
    assert result.rl_weighted["total_pnl"] == 0.0
    assert result.rl_weighted["sharpe_ratio"] == 0.0
    assert result.rl_weighted["max_drawdown"] == 0.0
    assert result.rl_weighted["equity_curve"] == []
    assert result.equal_weight["win_rate"] == 0.0
