"""Unit tests for db.py — uses a temp in-memory SQLite DB."""
import pytest
import os
from unittest.mock import patch


@pytest.fixture
def temp_db(tmp_path):
    db_path = str(tmp_path / "test.db")
    with patch("src.config.settings.DB_PATH", db_path):
        from importlib import reload
        import src.data.db as db
        reload(db)
        db.init_db()
        yield db


def test_init_db_creates_tables(temp_db):
    import sqlite3
    conn = sqlite3.connect(temp_db.settings.DB_PATH if hasattr(temp_db, 'settings') else "data/test.db")


def test_write_and_read_candles(temp_db):
    candles = [{"timestamp_ist": "2024-01-01T09:15:00", "open": 21000, "high": 21050, "low": 20990, "close": 21030, "volume": 100000}]
    temp_db.write_candles("NSE:NIFTY 50", candles)
    result = temp_db.read_candles("NSE:NIFTY 50", "2024-01-01", "2024-01-02")
    assert len(result) == 1
    assert result[0]["close"] == 21030
