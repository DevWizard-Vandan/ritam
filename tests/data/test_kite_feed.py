"""Unit tests for kite_feed.py with mocked yfinance-backed client calls."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch
import warnings

warnings.filterwarnings("ignore", message="\nPyarrow will become a required dependency of pandas", category=DeprecationWarning)

import pandas as pd
import pytz

from src.data import kite_feed
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
        count = kite_feed.fetch_historical_candles()

    assert count == 2
    mock_write.assert_called_once()
    symbol, candles = mock_write.call_args.args
    assert symbol == "NSE:NIFTY 50"
    assert candles[0]["open"] == 22200.0


def test_fetch_historical_candles_chunks_long_ranges_for_real_kite():
    mock_kite = MagicMock()
    mock_kite.__class__.__module__ = "kiteconnect.connect"
    mock_kite.historical_data.side_effect = [
        [
            {
                "date": IST.localize(datetime(2020, 1, 1, 0, 0)),
                "open": 100.0,
                "high": 110.0,
                "low": 95.0,
                "close": 105.0,
                "volume": 1000,
            }
        ],
        [
            {
                "date": IST.localize(datetime(2025, 3, 1, 0, 0)),
                "open": 200.0,
                "high": 210.0,
                "low": 195.0,
                "close": 205.0,
                "volume": 2000,
            }
        ],
    ]

    with patch("src.data.kite_feed.get_client", return_value=mock_kite), patch(
        "src.data.kite_feed.write_candles"
    ) as mock_write:
        count = kite_feed.fetch_historical_candles(
            from_date="2020-01-01",
            to_date="2025-12-31",
            interval="day",
        )

    assert count == 2
    assert mock_kite.historical_data.call_count == 2
    assert mock_write.call_args.args[1][0]["open"] == 100.0
    assert mock_write.call_args.args[1][1]["close"] == 205.0


def test_fetch_historical_candles_returns_zero_when_source_empty():
    empty_frame = pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])

    with patch("src.data.kite_feed.get_client", return_value=YFinanceKiteClient()), patch(
        "src.data.kite_client.yf.download", return_value=empty_frame
    ), patch(
        "src.data.kite_feed.write_candles"
    ) as mock_write:
        count = kite_feed.fetch_historical_candles()

    assert count == 0
    mock_write.assert_not_called()


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
