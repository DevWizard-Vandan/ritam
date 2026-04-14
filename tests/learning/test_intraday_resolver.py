import pytest
from src.data.db import init_db, get_connection, upsert_intraday_candles
from src.learning.intraday_resolver import resolve_intraday_outcomes
from src.config import settings

@pytest.fixture(autouse=True)
def mock_db_path(tmp_path, monkeypatch):
    db_file = tmp_path / "nested" / "test_market_intraday.db"
    monkeypatch.setattr(settings, "DB_PATH", str(db_file))
    init_db()
    return db_file

def _insert_prediction(timestamp, signal):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO predictions (timestamp, predicted_direction, predicted_move_pct, confidence, timeframe_minutes, regime, source)
            VALUES (?, ?, 0, 0.5, 15, 'regime', 'intraday')
        """, (timestamp, signal))
        conn.commit()

def test_resolve_intraday_outcomes_correct_buy():
    # Prediction
    pred_ts = "2026-04-14T09:15:00+05:30"
    _insert_prediction(pred_ts, "buy")

    # Entry candle + 5 forward candles
    symbol = settings.INTRADAY_SYMBOL
    candles = [
        {"timestamp_ist": "2026-04-14T09:15:00+05:30", "open": 100, "high": 100, "low": 100, "close": 100.0, "volume": 1000}, # entry
        {"timestamp_ist": "2026-04-14T09:30:00+05:30", "open": 100, "high": 100, "low": 100, "close": 100.1, "volume": 1000},
        {"timestamp_ist": "2026-04-14T09:45:00+05:30", "open": 100, "high": 100, "low": 100, "close": 100.1, "volume": 1000},
        {"timestamp_ist": "2026-04-14T10:00:00+05:30", "open": 100, "high": 100, "low": 100, "close": 100.2, "volume": 1000},
        {"timestamp_ist": "2026-04-14T10:15:00+05:30", "open": 100, "high": 100, "low": 100, "close": 100.2, "volume": 1000},
        {"timestamp_ist": "2026-04-14T10:30:00+05:30", "open": 100, "high": 100, "low": 100, "close": 100.3, "volume": 1000}, # +0.3% actual_return
    ]
    upsert_intraday_candles(symbol, candles)

    n = resolve_intraday_outcomes()
    assert n == 1

    with get_connection() as conn:
        err = conn.execute("SELECT direction_correct FROM prediction_errors").fetchone()
        assert err[0] == 1

def test_resolve_intraday_outcomes_incorrect_buy():
    pred_ts = "2026-04-14T09:15:00+05:30"
    _insert_prediction(pred_ts, "buy")

    symbol = settings.INTRADAY_SYMBOL
    candles = [
        {"timestamp_ist": "2026-04-14T09:15:00+05:30", "open": 100, "high": 100, "low": 100, "close": 100.0, "volume": 1000},
        {"timestamp_ist": "2026-04-14T09:30:00+05:30", "open": 100, "high": 100, "low": 100, "close": 100.0, "volume": 1000},
        {"timestamp_ist": "2026-04-14T09:45:00+05:30", "open": 100, "high": 100, "low": 100, "close": 100.0, "volume": 1000},
        {"timestamp_ist": "2026-04-14T10:00:00+05:30", "open": 100, "high": 100, "low": 100, "close": 100.0, "volume": 1000},
        {"timestamp_ist": "2026-04-14T10:15:00+05:30", "open": 100, "high": 100, "low": 100, "close": 100.0, "volume": 1000},
        {"timestamp_ist": "2026-04-14T10:30:00+05:30", "open": 100, "high": 100, "low": 100, "close": 99.8, "volume": 1000}, # -0.2% actual_return
    ]
    upsert_intraday_candles(symbol, candles)

    n = resolve_intraday_outcomes()
    assert n == 1

    with get_connection() as conn:
        err = conn.execute("SELECT direction_correct FROM prediction_errors").fetchone()
        assert err[0] == 0

def test_resolve_intraday_outcomes_correct_hold():
    pred_ts = "2026-04-14T09:15:00+05:30"
    _insert_prediction(pred_ts, "hold")

    symbol = settings.INTRADAY_SYMBOL
    candles = [
        {"timestamp_ist": "2026-04-14T09:15:00+05:30", "open": 100, "high": 100, "low": 100, "close": 100.0, "volume": 1000},
        {"timestamp_ist": "2026-04-14T09:30:00+05:30", "open": 100, "high": 100, "low": 100, "close": 100.0, "volume": 1000},
        {"timestamp_ist": "2026-04-14T09:45:00+05:30", "open": 100, "high": 100, "low": 100, "close": 100.0, "volume": 1000},
        {"timestamp_ist": "2026-04-14T10:00:00+05:30", "open": 100, "high": 100, "low": 100, "close": 100.0, "volume": 1000},
        {"timestamp_ist": "2026-04-14T10:15:00+05:30", "open": 100, "high": 100, "low": 100, "close": 100.0, "volume": 1000},
        {"timestamp_ist": "2026-04-14T10:30:00+05:30", "open": 100, "high": 100, "low": 100, "close": 100.1, "volume": 1000}, # +0.1% actual_return (neutral band)
    ]
    upsert_intraday_candles(symbol, candles)

    n = resolve_intraday_outcomes()
    assert n == 1

    with get_connection() as conn:
        err = conn.execute("SELECT direction_correct FROM prediction_errors").fetchone()
        assert err[0] == 1

def test_resolve_intraday_outcomes_skip_less_than_5_candles():
    pred_ts = "2026-04-14T09:15:00+05:30"
    _insert_prediction(pred_ts, "buy")

    symbol = settings.INTRADAY_SYMBOL
    candles = [
        {"timestamp_ist": "2026-04-14T09:15:00+05:30", "open": 100, "high": 100, "low": 100, "close": 100.0, "volume": 1000},
        {"timestamp_ist": "2026-04-14T09:30:00+05:30", "open": 100, "high": 100, "low": 100, "close": 100.0, "volume": 1000},
    ] # only 1 forward candle
    upsert_intraday_candles(symbol, candles)

    n = resolve_intraday_outcomes()
    assert n == 0

    with get_connection() as conn:
        err = conn.execute("SELECT COUNT(*) FROM prediction_errors").fetchone()
        assert err[0] == 0
