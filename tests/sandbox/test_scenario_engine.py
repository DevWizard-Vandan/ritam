import pytest
from unittest.mock import patch, MagicMock
import json

from src.sandbox.scenario_engine import ScenarioEngine, ScenarioResult

@pytest.fixture
def engine():
    return ScenarioEngine()

@patch("src.sandbox.scenario_engine.quick_reason")
@patch("src.sandbox.scenario_engine.deep_reason")
def test_run_condition_only(mock_deep_reason, mock_quick_reason, engine):
    mock_quick_reason.return_value = '{"type": "test"}'

    mock_deep_reason.return_value = json.dumps({
        "projected_candles": [{"close": 22100}],
        "regime": "Trending Up",
        "narrative": "A test narrative.",
        "confidence": 0.8
    })

    result = engine.run(condition="some condition", date=None)

    assert result.data_source == "gemini_pure"
    assert result.projected_candles == [{"close": 22100}]
    assert result.narrative == "A test narrative."
    assert result.regime == "Trending Up"
    assert result.confidence == 0.8

@patch("src.sandbox.scenario_engine.yf.download")
@patch("src.sandbox.scenario_engine.quick_reason")
@patch("src.sandbox.scenario_engine.find_analogs")
def test_run_date_yfinance_range(mock_find_analogs, mock_quick_reason, mock_yf, engine):
    import pandas as pd
    from datetime import datetime

    df = pd.DataFrame({
        'Open': [100.0],
        'High': [105.0],
        'Low': [95.0],
        'Close': [102.0],
        'Volume': [1000.0]
    }, index=[datetime(2008, 1, 15)])

    mock_yf.return_value = df
    mock_find_analogs.return_value = [{"start_date": "2000-01-01"}]

    mock_quick_reason.return_value = json.dumps({
        "projected_candles": [{"close": 110.0}],
        "regime": "Crisis",
        "narrative": "Global meltdown.",
        "confidence": 0.9
    })

    result = engine.run(condition=None, date="2008-01-15")

    assert result.data_source == "yfinance"
    assert len(result.historical_candles) == 1
    assert result.historical_candles[0]["close"] == 102.0
    assert result.projected_candles == [{"close": 110.0}]

@patch("src.sandbox.scenario_engine.read_intraday_candles")
@patch("src.sandbox.scenario_engine.quick_reason")
@patch("src.sandbox.scenario_engine.find_intraday_analogs")
def test_run_both_condition_and_date(mock_find_intraday_analogs, mock_quick_reason, mock_read_candles, engine):
    mock_read_candles.return_value = [
        {"timestamp_ist": "2024-01-01T09:15:00", "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 100},
        {"timestamp_ist": "2024-01-02T09:15:00", "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 100}
    ]

    mock_quick_reason.side_effect = [
        '{"type": "bull run"}',
        json.dumps({
            "projected_candles": [{"close": 23000}],
            "regime": "Ranging",
            "narrative": "Sideways market.",
            "confidence": 0.5
        })
    ]

    result = engine.run(condition="market rally", date="2024-01-01")

    assert result.condition_parsed == {"type": "bull run"}
    assert result.data_source == "db"
    assert result.projected_candles == [{"close": 23000}]

def test_raises_on_empty_input(engine):
    with pytest.raises(ValueError):
        engine.run(condition=None, date=None)

@patch("src.sandbox.scenario_engine.deep_reason")
def test_result_shape(mock_deep_reason, engine):
    mock_deep_reason.return_value = json.dumps({
        "projected_candles": [],
        "regime": "test",
        "narrative": "test",
        "confidence": 0.5
    })

    result = engine.run(condition="test", date=None)

    assert isinstance(result, ScenarioResult)
    assert hasattr(result, "date")
    assert hasattr(result, "condition")
    assert hasattr(result, "data_source")
    assert hasattr(result, "historical_candles")
    assert hasattr(result, "projected_candles")
    assert hasattr(result, "condition_parsed")
    assert hasattr(result, "regime")
    assert hasattr(result, "narrative")
    assert hasattr(result, "confidence")

    assert isinstance(result.data_source, str)
    assert isinstance(result.historical_candles, list)
    assert isinstance(result.projected_candles, list)
    assert isinstance(result.regime, str)
    assert isinstance(result.narrative, str)
    assert isinstance(result.confidence, float)
