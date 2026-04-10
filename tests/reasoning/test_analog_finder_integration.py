import pytest
from unittest.mock import patch

from src.reasoning.analog_finder import find_analogs

@patch('src.reasoning.analog_finder.read_candles')
def test_find_analogs_integration(mock_read_candles):
    """Test find_analogs() with a 10-row synthetic window and mock read_candles."""
    # Create 10-row synthetic current window
    # Returns from 100 will be approx 1% each day
    current_window = [
        {"timestamp_ist": f"2024-03-{day:02d}T15:30:00", "close": 100.0 + day}
        for day in range(1, 11)
    ]

    # Create 60-row synthetic historical data
    # Create similar returns of approx 1% for part of it so we get a decent match
    historical_data = [
        {"timestamp_ist": f"2020-03-{day:02d}T15:30:00", "close": 100.0 + day} if day <= 30 else
        {"timestamp_ist": f"2020-04-{day-30:02d}T15:30:00", "close": 130.0 - (day-30)}
        for day in range(1, 61)
    ]

    mock_read_candles.return_value = historical_data

    top_n = 3
    results = find_analogs(current_window, top_n=top_n)

    # Assert returned list has at most top_n items
    assert len(results) <= top_n

    # Assert each result has keys: start_date, end_date, similarity_score, next_5day_return
    for result in results:
        assert "start_date" in result
        assert "end_date" in result
        assert "similarity_score" in result
        assert "next_5day_return" in result
