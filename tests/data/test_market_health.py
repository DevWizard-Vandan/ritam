from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.data import market_health


IST = timezone(timedelta(hours=5, minutes=30))


class _KiteClient:
    __module__ = "kiteconnect"


class _YFinanceClient:
    __module__ = "yfinance"


def test_check_data_freshness_marks_intraday_data_ok(monkeypatch):
    monkeypatch.setattr(
        market_health,
        "read_intraday_candles",
        lambda symbol, limit=1: [
            {"timestamp_ist": "2026-04-25T10:00:00+05:30", "close": 100.0}
        ],
    )
    monkeypatch.setattr(
        market_health,
        "read_candles",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr(
        market_health,
        "get_client",
        lambda: _KiteClient(),
    )
    monkeypatch.setattr(
        market_health,
        "fetch_current_price",
        lambda symbol: {
            "source": "kite",
            "price": 101.0,
            "fetched_at": "2026-04-25T10:00:10+05:30",
        },
    )

    result = market_health.check_data_freshness(
        now_fn=lambda: datetime(2026, 4, 25, 10, 1, 0, tzinfo=IST),
    )

    assert result["status"] == "OK"
    assert result["data_source"] == "kite"
    assert result["table"] == "intraday_candles"
    assert result["last_candle_timestamp"] == "2026-04-25T10:00:00+05:30"
    assert result["delay_seconds"] == 60.0


def test_check_data_freshness_marks_stale_when_delay_exceeds_threshold(monkeypatch):
    monkeypatch.setattr(
        market_health,
        "read_intraday_candles",
        lambda symbol, limit=1: [
            {"timestamp_ist": "2026-04-25T09:55:00+05:30", "close": 100.0}
        ],
    )
    monkeypatch.setattr(
        market_health,
        "read_candles",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr(
        market_health,
        "get_client",
        lambda: _KiteClient(),
    )
    monkeypatch.setattr(
        market_health,
        "fetch_current_price",
        lambda symbol: {"source": "kite", "price": 101.0, "fetched_at": "2026-04-25T10:01:00+05:30"},
    )

    result = market_health.check_data_freshness(
        stale_after_seconds=120,
        now_fn=lambda: datetime(2026, 4, 25, 10, 3, 30, tzinfo=IST),
    )

    assert result["status"] == "STALE"
    assert result["delay_seconds"] == 510.0


def test_check_data_freshness_uses_daily_fallback_when_intraday_missing(monkeypatch):
    monkeypatch.setattr(
        market_health,
        "read_intraday_candles",
        lambda symbol, limit=1: [],
    )
    monkeypatch.setattr(
        market_health,
        "read_candles",
        lambda *args, **kwargs: [
            {"timestamp_ist": "2026-04-24T15:30:00+05:30", "close": 100.0}
        ],
    )
    monkeypatch.setattr(
        market_health,
        "get_client",
        lambda: _KiteClient(),
    )
    monkeypatch.setattr(
        market_health,
        "fetch_current_price",
        lambda symbol: {"source": "kite", "price": 101.0, "fetched_at": "2026-04-25T10:01:00+05:30"},
    )

    result = market_health.check_data_freshness(now_fn=lambda: datetime(2026, 4, 25, 10, 1, 0, tzinfo=IST))

    assert result["table"] == "candles"
    assert result["status"] == "STALE"


def test_check_data_freshness_returns_no_candle_status(monkeypatch):
    monkeypatch.setattr(
        market_health,
        "read_intraday_candles",
        lambda symbol, limit=1: [],
    )
    monkeypatch.setattr(
        market_health,
        "read_candles",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr(
        market_health,
        "get_client",
        lambda: _KiteClient(),
    )
    monkeypatch.setattr(
        market_health,
        "fetch_current_price",
        lambda symbol: {"source": "kite", "price": 101.0, "fetched_at": "2026-04-25T10:01:00+05:30"},
    )

    result = market_health.check_data_freshness(now_fn=lambda: datetime(2026, 4, 25, 10, 1, 0, tzinfo=IST))

    assert result["status"] == "STALE"
    assert result["reason"] == "no_candles_available"
    assert result["current_price"] == 101.0


def test_check_data_freshness_marks_yfinance_source(monkeypatch):
    monkeypatch.setattr(
        market_health,
        "read_intraday_candles",
        lambda symbol, limit=1: [
            {"timestamp_ist": "2026-04-25T10:00:00+05:30", "close": 100.0}
        ],
    )
    monkeypatch.setattr(
        market_health,
        "read_candles",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr(
        market_health,
        "get_client",
        lambda: _YFinanceClient(),
    )
    monkeypatch.setattr(
        market_health,
        "fetch_current_price",
        lambda symbol: {"source": "yfinance", "price": 100.5, "fetched_at": "2026-04-25T10:01:00+05:30"},
    )

    result = market_health.check_data_freshness(now_fn=lambda: datetime(2026, 4, 25, 10, 1, 0, tzinfo=IST))

    assert result["data_source"] == "yfinance"
    assert result["price_source"] == "yfinance"
