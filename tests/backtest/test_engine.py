"""Unit tests for src.backtest.engine."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import backtrader as bt
import pytest

from src.backtest.engine import (
    SimpleMovingAverageCrossover,
    load_nifty_data,
    run_backtest,
)


def _synthetic_candles(rows: int = 20) -> list[dict]:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    closes = [100, 99, 98, 99, 100, 101, 102, 103, 104, 103, 102, 101, 100, 99, 98, 99, 100, 101, 102, 103]

    candles = []
    for idx in range(rows):
        timestamp = start + timedelta(days=idx)
        close = closes[idx]
        candles.append(
            {
                "timestamp_ist": timestamp.isoformat(),
                "open": close - 0.5,
                "high": close + 1.0,
                "low": close - 1.0,
                "close": close,
                "volume": 1000 + idx,
            }
        )
    return candles


def test_load_nifty_data_returns_pandas_feed(monkeypatch):
    monkeypatch.setattr("src.backtest.engine.read_candles", lambda **_: _synthetic_candles())

    feed = load_nifty_data(start_date="2026-01-01", end_date="2026-01-31")

    assert isinstance(feed, bt.feeds.PandasData)


def test_load_nifty_data_raises_when_no_data(monkeypatch):
    monkeypatch.setattr("src.backtest.engine.read_candles", lambda **_: [])

    with pytest.raises(ValueError, match="No candle data"):
        load_nifty_data(start_date="2026-01-01", end_date="2026-01-31")


def test_run_backtest_returns_trade_log_and_metrics(monkeypatch):
    monkeypatch.setattr("src.backtest.engine.read_candles", lambda **_: _synthetic_candles())

    result = run_backtest(start_date="2026-01-01", end_date="2026-01-31")

    assert "trade_log" in result
    assert "metrics" in result
    assert isinstance(result["trade_log"], list)
    assert isinstance(result["metrics"], dict)


def test_run_backtest_metrics_include_required_keys(monkeypatch):
    monkeypatch.setattr("src.backtest.engine.read_candles", lambda **_: _synthetic_candles())

    result = run_backtest(start_date="2026-01-01", end_date="2026-01-31")

    metrics = result["metrics"]
    assert {"sharpe", "max_drawdown", "cagr"}.issubset(metrics.keys())


def test_default_strategy_is_sma_crossover():
    assert SimpleMovingAverageCrossover.__name__ == "SimpleMovingAverageCrossover"
