import pytest
import sqlite3
import os
from unittest.mock import patch, MagicMock
from src.data.db import init_db, get_connection, upsert_intraday_candles, read_intraday_candles, get_latest_intraday_timestamp
from src.data.intraday_seeder import seed_intraday_history, sync_intraday_today
from src.config import settings

@pytest.fixture(autouse=True)
def mock_db_path(tmp_path, monkeypatch):
    db_file = tmp_path / "nested" / "test_market_intraday.db"
    monkeypatch.setattr(settings, "DB_PATH", str(db_file))
    init_db()
    return db_file

def test_upsert_intraday_candles():
    symbol = "NSE:NIFTY 50"
    candles = [
        {"timestamp_ist": "2026-04-14T09:15:00+05:30", "open": 19000.0, "high": 19050.0, "low": 18990.0, "close": 19040.0, "volume": 10000},
        {"timestamp_ist": "2026-04-14T09:30:00+05:30", "open": 19040.0, "high": 19060.0, "low": 19030.0, "close": 19050.0, "volume": 15000}
    ]

    inserted = upsert_intraday_candles(symbol, candles)
    assert inserted == 2

    # Duplicate insert should ignore
    inserted = upsert_intraday_candles(symbol, candles)
    assert inserted == 0

def test_get_latest_intraday_timestamp():
    symbol = "NSE:NIFTY 50"
    assert get_latest_intraday_timestamp(symbol) is None

    candles = [
        {"timestamp_ist": "2026-04-14T09:15:00+05:30", "open": 19000.0, "high": 19050.0, "low": 18990.0, "close": 19040.0, "volume": 10000},
        {"timestamp_ist": "2026-04-14T09:30:00+05:30", "open": 19040.0, "high": 19060.0, "low": 19030.0, "close": 19050.0, "volume": 15000}
    ]
    upsert_intraday_candles(symbol, candles)

    assert get_latest_intraday_timestamp(symbol) == "2026-04-14T09:30:00+05:30"

def test_read_intraday_candles_limit():
    symbol = "NSE:NIFTY 50"
    candles = [
        {"timestamp_ist": "2026-04-14T09:15:00+05:30", "open": 19000.0, "high": 19050.0, "low": 18990.0, "close": 19040.0, "volume": 10000},
        {"timestamp_ist": "2026-04-14T09:30:00+05:30", "open": 19040.0, "high": 19060.0, "low": 19030.0, "close": 19050.0, "volume": 15000},
        {"timestamp_ist": "2026-04-14T09:45:00+05:30", "open": 19050.0, "high": 19100.0, "low": 19040.0, "close": 19080.0, "volume": 12000}
    ]
    upsert_intraday_candles(symbol, candles)

    read_data = read_intraday_candles(symbol, limit=2)
    assert len(read_data) == 2
    assert read_data[0]["timestamp_ist"] == "2026-04-14T09:30:00+05:30"
    assert read_data[1]["timestamp_ist"] == "2026-04-14T09:45:00+05:30"


@patch("src.data.kite_client.get_client")
def test_seed_intraday_history(mock_get_client):
    mock_kite = MagicMock()
    mock_get_client.return_value = mock_kite

    mock_kite.instruments.return_value = [{"instrument_token": 256265, "tradingsymbol": "NIFTY 50"}]

    # 5 sample candles
    import datetime
    from unittest.mock import Mock
    dt = datetime.datetime.now()
    mock_kite.historical_data.return_value = [
        {"date": dt, "open": 100, "high": 105, "low": 95, "close": 102, "volume": 1000}
        for _ in range(5)
    ]

    inserted = seed_intraday_history("NSE:NIFTY 50", days_back=1)

    # 5 inserted, since unique constraint uses timestamp, we need to ensure the mocks return different times
    # Actually wait, our mock just gave the same datetime 5 times. Let's make it distinct.

    assert mock_kite.historical_data.called

@patch("src.data.kite_client.get_client")
def test_seed_intraday_history_with_distinct_dates(mock_get_client):
    mock_kite = MagicMock()
    mock_get_client.return_value = mock_kite
    mock_kite.instruments.return_value = [{"instrument_token": 256265, "tradingsymbol": "NIFTY 50"}]

    import datetime
    mock_kite.historical_data.return_value = [
        {"date": datetime.datetime(2026, 4, 14, 9, 15), "open": 100, "high": 105, "low": 95, "close": 102, "volume": 1000},
        {"date": datetime.datetime(2026, 4, 14, 9, 30), "open": 100, "high": 105, "low": 95, "close": 102, "volume": 1000},
        {"date": datetime.datetime(2026, 4, 14, 9, 45), "open": 100, "high": 105, "low": 95, "close": 102, "volume": 1000},
        {"date": datetime.datetime(2026, 4, 14, 10, 0), "open": 100, "high": 105, "low": 95, "close": 102, "volume": 1000},
        {"date": datetime.datetime(2026, 4, 14, 10, 15), "open": 100, "high": 105, "low": 95, "close": 102, "volume": 1000}
    ]

    inserted = seed_intraday_history("NSE:NIFTY 50", days_back=1)
    assert inserted == 5
