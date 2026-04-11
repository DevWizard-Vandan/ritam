"""Unit tests for kite_feed.py with mocked yfinance-backed client calls."""
from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import call, patch
import warnings

warnings.filterwarnings("ignore", message="\nPyarrow will become a required dependency of pandas", category=DeprecationWarning)

import pandas as pd
import pytz

from src.data import kite_feed
from src.data.kite_feed import _date_chunks
from src.data.kite_client import YFinanceKiteClient

IST = pytz.timezone("Asia/Kolkata")


class _FrozenDateTime(datetime):
    frozen_now: datetime = IST.localize(datetime(2026, 4, 9, 10, 0))

    @classmethod
    def now(cls, tz=None):  # noqa: D401
        value = cls.frozen_now
        if tz is None:
            return value.replace(tzinfo=None)
        return value.astimezone(tz)


def _daily_frame() -> pd.DataFrame:
    index = pd.DatetimeIndex(
        [
            pd.Timestamp("2026-04-07 00:00:00", tz="Asia/Kolkata"),
            pd.Timestamp("2026-04-08 00:00:00", tz="Asia/Kolkata"),
        ]
    )
    return pd.DataFrame(
        {
            "Open": [22200.0, 22310.0],
            "High": [22320.0, 22400.0],
            "Low": [22190.0, 22250.0],
            "Close": [22300.0, 22380.0],
            "Volume": [120000, 110000],
        },
        index=index,
    )


def _minute_frame() -> pd.DataFrame:
    index = pd.DatetimeIndex(
        [
            pd.Timestamp("2026-04-09 09:15:00", tz="Asia/Kolkata"),
            pd.Timestamp("2026-04-09 09:16:00", tz="Asia/Kolkata"),
        ]
    )
    return pd.DataFrame(
        {
            "Open": [22380.0, 22382.0],
            "High": [22385.0, 22390.0],
            "Low": [22370.0, 22375.0],
            "Close": [22383.0, 22388.0],
            "Volume": [5000, 6200],
        },
        index=index,
    )


def test_fetch_historical_candles_downloads_and_writes_daily_data():
    with patch("src.data.kite_feed.get_client", return_value=YFinanceKiteClient()), patch(
        "src.data.kite_client.yf.download", return_value=_daily_frame()
    ), patch(
        "src.data.kite_feed.write_candles"
    ) as mock_write:
        # Use a narrow window (< 1800 days) so only one chunk is produced.
        count = kite_feed.fetch_historical_candles(from_date="2026-04-07", to_date="2026-04-09")

    assert count == 2
    mock_write.assert_called_once()
    symbol, candles = mock_write.call_args.args
    assert symbol == "NSE:NIFTY 50"
    assert candles[0]["open"] == 22200.0


def test_fetch_historical_candles_returns_zero_when_source_empty():
    empty_frame = pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])

    with patch("src.data.kite_feed.get_client", return_value=YFinanceKiteClient()), patch(
        "src.data.kite_client.yf.download", return_value=empty_frame
    ), patch(
        "src.data.kite_feed.write_candles"
    ) as mock_write:
        # Narrow window to keep the test fast (still exercises the zero-record path).
        count = kite_feed.fetch_historical_candles(from_date="2026-04-07", to_date="2026-04-09")

    assert count == 0
    mock_write.assert_not_called()


def test_fetch_historical_candles_chunks_large_date_range():
    """fetch_historical_candles splits a 3600-day range into two 1800-day chunks."""
    start = IST.localize(datetime(2020, 1, 1))
    # 3600-day span → 2 chunks of 1800 days each.
    end_date = (start + timedelta(days=3600)).strftime("%Y-%m-%d")

    # Each chunk call returns 2 candles; expect 4 total across 2 chunks.
    with patch("src.data.kite_feed.get_client", return_value=YFinanceKiteClient()), patch(
        "src.data.kite_client.yf.download", return_value=_daily_frame()
    ), patch(
        "src.data.kite_feed.write_candles"
    ) as mock_write:
        count = kite_feed.fetch_historical_candles(from_date="2020-01-01", to_date=end_date)

    assert count == 4
    mock_write.assert_called_once()
    _, candles = mock_write.call_args.args
    assert len(candles) == 4


def test_fetch_intraday_candles_downloads_market_window_data():
    _FrozenDateTime.frozen_now = IST.localize(datetime(2026, 4, 9, 10, 20))

    with patch("src.data.kite_feed.datetime", _FrozenDateTime), patch(
        "src.data.kite_feed.get_client", return_value=YFinanceKiteClient()
    ), patch(
        "src.data.kite_client.yf.download", return_value=_minute_frame()
    ) as mock_download, patch("src.data.kite_feed.write_candles") as mock_write:
        count = kite_feed.fetch_intraday_candles()

    assert count == 2
    assert mock_download.call_args.kwargs["interval"] == "1m"
    assert mock_write.call_args.args[0] == "NSE:NIFTY 50"


def test_fetch_intraday_candles_skips_before_market_open():
    _FrozenDateTime.frozen_now = IST.localize(datetime(2026, 4, 9, 9, 0))

    with patch("src.data.kite_feed.datetime", _FrozenDateTime), patch(
        "src.data.kite_client.yf.download"
    ) as mock_download:
        count = kite_feed.fetch_intraday_candles()

    assert count == 0
    mock_download.assert_not_called()


def test_fetch_intraday_candles_skips_after_market_close():
    _FrozenDateTime.frozen_now = IST.localize(datetime(2026, 4, 9, 16, 5))

    with patch("src.data.kite_feed.datetime", _FrozenDateTime), patch(
        "src.data.kite_client.yf.download"
    ) as mock_download:
        count = kite_feed.fetch_intraday_candles()

    assert count == 0
    mock_download.assert_not_called()


def test_start_live_feed_registers_60_second_job_and_starts_scheduler():
    with patch("src.data.kite_feed.BackgroundScheduler") as mock_scheduler_cls:
        scheduler = mock_scheduler_cls.return_value

        returned = kite_feed.start_live_feed()

    assert returned is scheduler
    scheduler.add_job.assert_called_once()
    kwargs = scheduler.add_job.call_args.kwargs
    assert kwargs["trigger"] == "cron"
    assert kwargs["second"] == "0"
    scheduler.start.assert_called_once()


# ---------------------------------------------------------------------------
# _date_chunks tests
# ---------------------------------------------------------------------------

def test_date_chunks_single_chunk_when_range_within_limit():
    start = IST.localize(datetime(2024, 1, 1))
    end = IST.localize(datetime(2024, 6, 1))
    chunks = list(_date_chunks(start, end))
    assert len(chunks) == 1
    assert chunks[0] == (start, end)


def test_date_chunks_splits_exactly_at_boundary():
    start = IST.localize(datetime(2020, 1, 1))
    # After chunk 1, cursor = start+1801. We need end > start+1801 (i.e. >= start+1802)
    # to satisfy cursor < end and produce a second chunk.
    end = start + timedelta(days=1802)
    chunks = list(_date_chunks(start, end, chunk_days=1800))
    assert len(chunks) == 2
    # First chunk ends at start + 1800 days.
    assert chunks[0][1] == start + timedelta(days=1800)
    # Second chunk starts one day after the first ends.
    assert chunks[1][0] == start + timedelta(days=1801)
    assert chunks[1][1] == end


def test_date_chunks_consecutive_chunks_are_contiguous():
    start = IST.localize(datetime(2000, 1, 1))
    end = IST.localize(datetime(2025, 1, 1))
    chunks = list(_date_chunks(start, end, chunk_days=1800))
    assert len(chunks) >= 2
    for i in range(1, len(chunks)):
        prev_end = chunks[i - 1][1]
        curr_start = chunks[i][0]
        assert curr_start == prev_end + timedelta(days=1)


def test_date_chunks_last_chunk_ends_at_end():
    start = IST.localize(datetime(2000, 1, 1))
    end = IST.localize(datetime(2024, 12, 31))
    chunks = list(_date_chunks(start, end, chunk_days=1800))
    assert chunks[-1][1] == end


def test_date_chunks_covers_full_historical_seed_range():
    """The canonical seed range (2000-01-01 to 2024-12-31) must stay below 2000 days per chunk."""
    start = IST.localize(datetime(2000, 1, 1))
    end = IST.localize(datetime(2024, 12, 31))
    chunks = list(_date_chunks(start, end))
    for chunk_start, chunk_end in chunks:
        span = (chunk_end - chunk_start).days
        assert span <= 1800, f"Chunk span {span} exceeds 1800-day chunk size (Kite limit is 2000 days)"
