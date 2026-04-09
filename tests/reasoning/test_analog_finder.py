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
def test_find_analogs_respects_top_n_and_sorts_desc(mock_read_candles):
    current_window = _candles_from_closes([100, 101, 102])
    historical = _candles_from_closes([100, 101, 102, 103, 104, 105, 106, 100, 100, 100, 100], start_day=1)
    mock_read_candles.return_value = historical

    results = find_analogs(current_window, top_n=2)

    assert len(results) == 2
    assert results[0]["similarity_score"] >= results[1]["similarity_score"]


@patch("src.reasoning.analog_finder.read_candles")
def test_find_analogs_returns_empty_for_short_current_window(mock_read_candles):
    mock_read_candles.return_value = _candles_from_closes([100, 101, 102, 103, 104, 105], start_day=1)

    assert find_analogs([{"timestamp_ist": "2020-01-01", "close": 100}], top_n=3) == []


@patch("src.reasoning.analog_finder.read_candles")
def test_find_analogs_returns_empty_when_historical_data_is_insufficient(mock_read_candles):
    current_window = _candles_from_closes([100, 101, 102, 103])
    # Needs at least window_len + 5 = 9
    mock_read_candles.return_value = _candles_from_closes([100, 101, 102, 103, 104, 105, 106, 107], start_day=1)

    assert find_analogs(current_window, top_n=3) == []


@patch("src.reasoning.analog_finder.read_candles")
def test_find_analogs_computes_next_5day_return(mock_read_candles):
    current_window = _candles_from_closes([100, 101, 102])
    historical = _candles_from_closes([100, 101, 102, 120, 120, 120, 120, 120], start_day=1)
    mock_read_candles.return_value = historical

    results = find_analogs(current_window, top_n=1)

    # Window end close = 102 (day 3), day+5 close = 120 (day 8)
    expected = round(((120 - 102) / 102) * 100.0, 4)
    assert results[0]["next_5day_return"] == expected


@patch("src.reasoning.analog_finder.read_candles")
def test_find_analogs_returns_empty_for_non_positive_top_n(mock_read_candles):
    current_window = _candles_from_closes([100, 101, 102])
    mock_read_candles.return_value = _candles_from_closes([100, 101, 102, 103, 104, 105, 106, 107], start_day=1)

    assert find_analogs(current_window, top_n=0) == []
