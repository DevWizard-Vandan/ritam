import pytest
from unittest.mock import patch
from src.reasoning.analog_explainer import AnalogExplainer
from src.orchestrator.agent import OrchestratorResult

@patch("src.reasoning.analog_explainer.deep_reason")
def test_analog_explainer(mock_deep_reason):
    mock_deep_reason.return_value = "Market looks bullish."
    explainer = AnalogExplainer()
    analogs = [
        {"start_date": "2020-01-01", "end_date": "2020-01-20", "similarity_score": 0.9, "next_5day_return": 5.0},
        {"start_date": "2019-01-01", "end_date": "2019-01-20", "similarity_score": 0.8, "next_5day_return": 4.0},
        {"start_date": "2018-01-01", "end_date": "2018-01-20", "similarity_score": 0.7, "next_5day_return": -1.0},
    ]
    explanation = explainer.explain(current_candles=[], analogs=analogs, regime="trending_up", sentiment_score=0.5)

    assert explanation == "Market looks bullish."

    # Verify prompt contents
    prompt = mock_deep_reason.call_args[0][0]
    assert "trending_up" in prompt
    assert "0.5" in prompt
    assert "2020-01-01 to 2020-01-20" in prompt

    # Assert explanation is included in OrchestratorResult (mocking instantiation)
    result = OrchestratorResult(regime="trending_up", sentiment_score=0.5, top_analogs=analogs, signal="buy", explanation=explanation)
    assert result.explanation == "Market looks bullish."
