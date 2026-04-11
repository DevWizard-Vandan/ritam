"""Unit tests for kite_client.py using mocked yfinance responses."""
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import warnings

warnings.filterwarnings("ignore", message="\nPyarrow will become a required dependency of pandas", category=DeprecationWarning)

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


def _multi_index_frame() -> pd.DataFrame:
    index = pd.DatetimeIndex(
        [
            pd.Timestamp("2026-04-08 09:15:00", tz="Asia/Kolkata"),
            pd.Timestamp("2026-04-08 09:16:00", tz="Asia/Kolkata"),
        ]
    )
    columns = pd.MultiIndex.from_tuples(
        [
            ("Open", "^NSEI"),
            ("High", "^NSEI"),
            ("Low", "^NSEI"),
            ("Close", "^NSEI"),
            ("Volume", "^NSEI"),
        ]
    )
    return pd.DataFrame(
        [
            [22400.0, 22420.0, 22390.0, 22415.0, 1000],
            [22410.0, 22425.0, 22400.0, 22405.0, 1200],
        ],
        index=index,
        columns=columns,
    )


def test_get_client_returns_compatibility_adapter():
    with patch.object(kite_client.settings, "KITE_API_KEY", "your_api_key_here"), patch.object(
        kite_client.settings, "KITE_ACCESS_TOKEN", "your_access_token_here"
    ):
        client = kite_client.get_client()

    assert isinstance(client, kite_client.YFinanceKiteClient)
    assert client.api_key == "your_api_key_here"
    assert client.access_token == "your_access_token_here"


def test_get_client_returns_real_kite_client_when_credentials_present():
    mock_kite = MagicMock()
    fake_module = SimpleNamespace(KiteConnect=MagicMock(return_value=mock_kite))

    with patch.object(kite_client.settings, "KITE_API_KEY", "real-key"), patch.object(
        kite_client.settings, "KITE_ACCESS_TOKEN", "real-token"
    ), patch.dict("sys.modules", {"kiteconnect": fake_module}):
        client = kite_client.get_client()

    assert client is mock_kite
    fake_module.KiteConnect.assert_called_once_with(api_key="real-key")
    mock_kite.set_access_token.assert_called_once_with("real-token")


def test_set_access_token_updates_client_state():
    client = kite_client.YFinanceKiteClient()

    client.set_access_token("new-token")

    assert client.access_token == "new-token"


def test_historical_data_maps_nifty_token_to_nsei():
    client = kite_client.YFinanceKiteClient()
    with patch("src.data.kite_client.yf.download", return_value=_multi_index_frame()) as mock_download:
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


def test_historical_data_handles_flat_columns_without_iloc_errors():
    client = kite_client.YFinanceKiteClient()
    with patch("src.data.kite_client.yf.download", return_value=_sample_frame()):
        candles = client.historical_data(
            instrument_token=256265,
            from_date=datetime(2026, 4, 8, 9, 15),
            to_date=datetime(2026, 4, 8, 9, 16),
            interval="minute",
        )

    assert candles[1]["close"] == 22405.0


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
