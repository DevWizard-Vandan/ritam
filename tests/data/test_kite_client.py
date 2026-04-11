"""Unit tests for kite_client.py using mocked yfinance responses."""
from datetime import datetime
from importlib import reload
from unittest.mock import patch

import pandas as pd

import src.data.kite_client as kite_client


def _sample_frame() -> pd.DataFrame:
    index = pd.DatetimeIndex(
        [
            pd.Timestamp("2026-04-08 09:15:00", tz="Asia/Kolkata"),
            pd.Timestamp("2026-04-08 09:16:00", tz="Asia/Kolkata"),
        ]
    )
    return pd.DataFrame(
        {
            "Open": [22400.0, 22410.0],
            "High": [22420.0, 22425.0],
            "Low": [22390.0, 22400.0],
            "Close": [22415.0, 22405.0],
            "Volume": [1000, 1200],
        },
        index=index,
    )


def test_get_client_returns_compatibility_adapter():
    with patch("src.data.kite_client.settings") as mock_settings:
        mock_settings.KITE_API_KEY = "unused-key"
        mock_settings.KITE_ACCESS_TOKEN = "seed-token"

        reload(kite_client)

        # apply the mock onto the reloaded module
        kite_client.settings = mock_settings

        client = kite_client.get_client()

    assert isinstance(client, kite_client.YFinanceKiteClient)
    assert client.api_key == "unused-key"
    assert client.access_token == "seed-token"


def test_set_access_token_updates_client_state():
    client = kite_client.YFinanceKiteClient()

    client.set_access_token("new-token")

    assert client.access_token == "new-token"


def test_historical_data_maps_nifty_token_to_nsei():
    client = kite_client.YFinanceKiteClient()
    with patch("src.data.kite_client.yf.download", return_value=_sample_frame()) as mock_download:
        candles = client.historical_data(
            instrument_token=256265,
            from_date=datetime(2026, 4, 8, 9, 15),
            to_date=datetime(2026, 4, 8, 9, 16),
            interval="minute",
        )

    assert len(candles) == 2
    assert candles[0]["open"] == 22400.0
    assert candles[0]["date"].tzinfo is not None
    assert mock_download.call_args.kwargs["tickers"] == "^NSEI"
    assert mock_download.call_args.kwargs["interval"] == "1m"


def test_historical_data_maps_bank_nifty_token_to_nsebank():
    client = kite_client.YFinanceKiteClient()
    with patch("src.data.kite_client.yf.download", return_value=_sample_frame()) as mock_download:
        client.historical_data(
            instrument_token=260105,
            from_date="2026-04-08T09:15:00+05:30",
            to_date="2026-04-08T09:16:00+05:30",
            interval="minute",
        )

    assert mock_download.call_args.kwargs["tickers"] == "^NSEBANK"


def test_historical_data_returns_empty_list_for_empty_response():
    client = kite_client.YFinanceKiteClient()
    empty_frame = pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])

    with patch("src.data.kite_client.yf.download", return_value=empty_frame):
        candles = client.historical_data(
            instrument_token=256265,
            from_date=datetime(2026, 4, 8, 9, 15),
            to_date=datetime(2026, 4, 8, 9, 16),
            interval="minute",
        )

    assert candles == []


def test_historical_data_returns_empty_list_when_download_fails():
    client = kite_client.YFinanceKiteClient()

    with patch("src.data.kite_client.yf.download", side_effect=RuntimeError("network down")):
        candles = client.historical_data(
            instrument_token=256265,
            from_date=datetime(2026, 4, 8, 9, 15),
            to_date=datetime(2026, 4, 8, 9, 16),
            interval="minute",
        )

    assert candles == []
