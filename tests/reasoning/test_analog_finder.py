from unittest.mock import patch

from src.reasoning.analog_finder import find_analogs, find_intraday_analogs


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


def _intraday_candles_from_closes(closes: list[float]) -> list[dict]:
    """Generate synthetic 15-min intraday candles (9:15 + 15-min steps)."""
    candles = []
    # Spread across multiple days as needed (each day has 25 slots: 09:15–15:30)
    slots_per_day = 25
    for idx, close in enumerate(closes):
        day = idx // slots_per_day + 1
        slot = idx % slots_per_day
        minutes_from_start = slot * 15 + 15
        hour = 9 + minutes_from_start // 60
        minute = minutes_from_start % 60
        candles.append(
            {
                "timestamp_ist": (
                    f"2020-01-{day:02d}T{hour:02d}:{minute:02d}:00+05:30"
                ),
                "open": close,
                "high": close,
                "low": close,
                "close": close,
                "volume": 1000,
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


# ── find_intraday_analogs tests ──────────────────────────────────────────────


@patch("src.reasoning.analog_finder.read_intraday_candles")
def test_find_intraday_analogs_returns_top_n(mock_read_intraday):
    """Synthetic 15-min candles: verify top_n matches are returned."""
    # current window of 3 candles, historical of 30 (enough for window_len=3 + 5 outcome)
    historical = _intraday_candles_from_closes(
        [100.0 + i * 0.5 for i in range(30)]
    )
    mock_read_intraday.return_value = historical

    current_window = _intraday_candles_from_closes([100.0, 100.5, 101.0])
    results = find_intraday_analogs(current_window, top_n=2, window_size=3)

    assert len(results) == 2


@patch("src.reasoning.analog_finder.read_intraday_candles")
def test_find_intraday_analogs_insufficient_data(mock_read_intraday):
    """Fewer than window_size candles in history → returns []."""
    # Only 4 historical rows; need at least window_len(2) + 5 = 7
    historical = _intraday_candles_from_closes([100.0, 101.0, 102.0, 103.0])
    mock_read_intraday.return_value = historical

    current_window = _intraday_candles_from_closes([100.0, 101.0])
    results = find_intraday_analogs(current_window, top_n=3)

    assert results == []


@patch("src.reasoning.analog_finder.read_intraday_candles")
def test_find_intraday_analogs_current_window_smaller_than_window_size(mock_read_intraday):
    """current_window shorter than window_size → returns [] immediately (no DB call needed)."""
    mock_read_intraday.return_value = []

    # 3-candle window but window_size=20 → guard fires before any DB query
    current_window = _intraday_candles_from_closes([100.0, 101.0, 102.0])
    results = find_intraday_analogs(current_window, top_n=3, window_size=20)

    assert results == []
    mock_read_intraday.assert_not_called()


@patch("src.reasoning.analog_finder.read_intraday_candles")
def test_find_intraday_analogs_result_shape(mock_read_intraday):
    """Verify returned dicts contain exactly the expected keys."""
    historical = _intraday_candles_from_closes(
        [100.0 + i * 0.3 for i in range(20)]
    )
    mock_read_intraday.return_value = historical

    current_window = _intraday_candles_from_closes([100.0, 100.3, 100.6])
    results = find_intraday_analogs(current_window, top_n=1, window_size=3)

    assert len(results) == 1
    assert set(results[0].keys()) == {
        "start_date",
        "end_date",
        "similarity_score",
        "next_5candle_return",
    }


@patch("src.reasoning.analog_finder.read_intraday_candles")
def test_find_intraday_analogs_outcome_is_5_candles(mock_read_intraday):
    """Verify the outcome is computed exactly 5 candles forward from the window end."""
    # Build a known sequence: window ends at index (window_len-1), outcome at index (window_len+4)
    # Use a flat then jump pattern so the outcome is deterministic.
    closes = [100.0] * 7 + [200.0]  # 7 flat, then one jump at index 7
    # current_window = closes[0:2] (len=2), window_len=2
    # end_idx = 1, next_idx = 1+5 = 6, so outcome uses closes[1]=100 and closes[6]=100 → 0%
    # But the first match window is [0:2], outcome = closes[6] / closes[1] - 1 = 0%
    # The match at window [2:4] would give outcome at closes[8] which doesn't exist, etc.
    # Simpler: window of 2 candles, history of exactly 7 rows
    historical = _intraday_candles_from_closes([100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 110.0])
    mock_read_intraday.return_value = historical

    current_window = _intraday_candles_from_closes([100.0, 101.0])
    results = find_intraday_analogs(current_window, top_n=5, window_size=2)

    # Only one valid window: start=0, end=1, outcome at index 6 (=110.0)
    # next_5candle_return = (110 - 101) / 101 * 100
    assert len(results) == 1
    expected_return = round(((110.0 - 101.0) / 101.0) * 100.0, 4)
    assert results[0]["next_5candle_return"] == expected_return

