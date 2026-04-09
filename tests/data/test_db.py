import pytest
import sqlite3
import os
from src.data.db import init_db, get_connection, write_candles, read_candles
from src.config import settings

@pytest.fixture(autouse=True)
def mock_db_path(tmp_path, monkeypatch):
    """Fixture to mock settings.DB_PATH to a temporary file for tests."""
    db_file = tmp_path / "test_market.db"
    monkeypatch.setattr(settings, "DB_PATH", str(db_file))
    return db_file

def test_get_connection_creates_dir(mock_db_path):
    """Test that get_connection creates the directory if it doesn't exist."""
    # The fixture already sets DB_PATH. Let's make sure it creates the dir
    conn = get_connection()
    assert os.path.exists(os.path.dirname(settings.DB_PATH))
    assert isinstance(conn, sqlite3.Connection)
    conn.close()

def test_init_db_creates_tables():
    """Test that init_db creates all expected tables."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

    assert "candles" in tables
    assert "headlines" in tables
    assert "predictions" in tables
    assert "prediction_errors" in tables

def test_write_and_read_candles():
    """Test writing candles and reading them back correctly."""
    init_db()
    symbol = "NSE:NIFTY 50"
    candles = [
        {"timestamp_ist": "2023-10-25T09:15:00+05:30", "open": 19000.0, "high": 19050.0, "low": 18990.0, "close": 19040.0, "volume": 10000},
        {"timestamp_ist": "2023-10-25T09:16:00+05:30", "open": 19040.0, "high": 19060.0, "low": 19030.0, "close": 19050.0, "volume": 15000}
    ]

    write_candles(symbol, candles)

    # Read back within range
    read_data = read_candles(symbol, "2023-10-25T09:10:00+05:30", "2023-10-25T09:20:00+05:30")
    assert len(read_data) == 2
    assert read_data[0]["open"] == 19000.0
    assert read_data[1]["volume"] == 15000

def test_write_candles_ignores_duplicates():
    """Test that writing duplicate candles is ignored due to UNIQUE constraint."""
    init_db()
    symbol = "NSE:NIFTY 50"
    candles = [
        {"timestamp_ist": "2023-10-25T09:15:00+05:30", "open": 19000.0, "high": 19050.0, "low": 18990.0, "close": 19040.0, "volume": 10000}
    ]

    # Write once
    write_candles(symbol, candles)

    # Write again (duplicate)
    write_candles(symbol, candles)

    # Read back, should only be one entry
    read_data = read_candles(symbol, "2023-10-25T09:00:00+05:30", "2023-10-25T10:00:00+05:30")
    assert len(read_data) == 1

def test_read_candles_outside_range():
    """Test reading candles with date ranges that don't match any data."""
    init_db()
    symbol = "NSE:NIFTY 50"
    candles = [
        {"timestamp_ist": "2023-10-25T09:15:00+05:30", "open": 19000.0, "high": 19050.0, "low": 18990.0, "close": 19040.0, "volume": 10000}
    ]
    write_candles(symbol, candles)

    # Read with range outside the written candle
    read_data = read_candles(symbol, "2023-10-26T09:00:00+05:30", "2023-10-26T10:00:00+05:30")
    assert len(read_data) == 0
