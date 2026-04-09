from unittest.mock import patch

from src.reasoning.analog_finder import find_analogs


def _candles_from_closes(closes: list[float], start_day: int = 1) -> list[dict]:
    candles = []
    for idx, close in enumerate(closes):
        day = start_day + idx
        candles.append(
            {
                "timestamp_ist": f"2020-01-{day:02d}T15:30:00+05:30",
                "close": close,
            }
        )
    return candles


@patch("src.reasoning.analog_finder.read_candles")
def test_find_analogs_returns_expected_fields(mock_read_candles):
    current_window = _candles_from_closes([100, 101, 102])
    historical = _candles_from_closes([100, 101, 102, 103, 104, 105, 106, 100, 99, 98], start_day=1)
    mock_read_candles.return_value = historical

    results = find_analogs(current_window, top_n=1)

    assert len(results) == 1
    assert set(results[0].keys()) == {"start_date", "end_date", "similarity_score", "next_5day_return"}


@patch("src.reasoning.analog_finder.read_candles")
def test_find_analogs_uses_symbol_and_expected_date_range(mock_read_candles):
    current_window = _candles_from_closes([100, 101, 102])
    historical = _candles_from_closes([100, 101, 102, 103, 104, 105, 106, 100, 100, 100, 100], start_day=1)
    mock_read_candles.return_value = historical

    find_analogs(current_window, top_n=2, symbol="NSE:BANKNIFTY")

    mock_read_candles.assert_called_once_with(
        symbol="NSE:BANKNIFTY",
        from_date="2000-01-01",
        to_date="2100-01-01",
    )


@patch("src.reasoning.analog_finder.read_candles")
def test_find_analogs_returns_empty_for_short_current_window(mock_read_candles):
    mock_read_candles.return_value = _candles_from_closes([100, 101, 102, 103, 104, 105], start_day=1)

    assert find_analogs([{"timestamp_ist": "2020-01-01", "close": 100}], top_n=3) == []


@patch("src.reasoning.analog_finder.read_candles")
def test_find_analogs_returns_empty_when_historical_data_is_insufficient(mock_read_candles):
    current_window = _candles_from_closes([100, 101, 102, 103])
    # Needs at least window_len + 5 = 9 daily candles
    mock_read_candles.return_value = _candles_from_closes([100, 101, 102, 103, 104, 105, 106, 107], start_day=1)

    assert find_analogs(current_window, top_n=3) == []


@patch("src.reasoning.analog_finder.read_candles")
def test_find_analogs_collapses_intraday_rows_before_next_5day_return(mock_read_candles):
    current_window = _candles_from_closes([100, 110, 121])
    mock_read_candles.return_value = [
        {"timestamp_ist": "2020-01-01T09:15:00+05:30", "close": 90},
        {"timestamp_ist": "2020-01-01T15:30:00+05:30", "close": 100},
        {"timestamp_ist": "2020-01-02T15:30:00+05:30", "close": 110},
        {"timestamp_ist": "2020-01-03T15:30:00+05:30", "close": 121},
        {"timestamp_ist": "2020-01-04T15:30:00+05:30", "close": 130},
        {"timestamp_ist": "2020-01-05T15:30:00+05:30", "close": 140},
        {"timestamp_ist": "2020-01-06T15:30:00+05:30", "close": 150},
        {"timestamp_ist": "2020-01-07T15:30:00+05:30", "close": 160},
        {"timestamp_ist": "2020-01-08T15:30:00+05:30", "close": 170},
    ]

    results = find_analogs(current_window, top_n=1)

    expected = round(((170 - 121) / 121) * 100.0, 4)
    assert results[0]["next_5day_return"] == expected


@patch("src.reasoning.analog_finder.read_candles")
def test_find_analogs_returns_empty_for_non_positive_top_n(mock_read_candles):
    current_window = _candles_from_closes([100, 101, 102])
    mock_read_candles.return_value = _candles_from_closes([100, 101, 102, 103, 104, 105, 106, 107], start_day=1)

    assert find_analogs(current_window, top_n=0) == []
