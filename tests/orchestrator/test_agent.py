from unittest.mock import patch

from src.orchestrator.agent import MarketOrchestrator, OrchestratorResult


@patch("src.orchestrator.agent.find_analogs")
@patch("src.orchestrator.agent.classify_regime")
@patch("src.orchestrator.agent.score_headlines")
@patch("src.orchestrator.agent.fetch_headlines")
def test_run_cycle_returns_orchestrator_result_with_expected_fields(
    mock_fetch_headlines,
    mock_score_headlines,
    mock_classify_regime,
    mock_find_analogs,
):
    mock_fetch_headlines.return_value = ["headline 1", "headline 2"]
    mock_score_headlines.return_value = [{"score": 0.2}, {"score": 0.0}]
    mock_classify_regime.return_value = "baseline"
    mock_find_analogs.return_value = [{"start_date": "2020-01-01", "end_date": "2020-01-20"}]

    orchestrator = MarketOrchestrator(analog_top_n=2)
    result = orchestrator.run_cycle(
        last_candle={"price_change_pct": 0.5},
        recent_daily_candles=[{"close": 100}] * 20,
        vix=14.5,
    )

    assert isinstance(result, OrchestratorResult)
    assert result.regime == "baseline"
    assert result.sentiment_score == 0.1
    assert result.top_analogs == [{"start_date": "2020-01-01", "end_date": "2020-01-20"}]
    assert result.signal == "hold"


@patch("src.orchestrator.agent.find_analogs")
@patch("src.orchestrator.agent.classify_regime")
@patch("src.orchestrator.agent.score_headlines")
@patch("src.orchestrator.agent.fetch_headlines")
def test_run_cycle_emits_buy_signal_when_conditions_match(
    mock_fetch_headlines,
    mock_score_headlines,
    mock_classify_regime,
    mock_find_analogs,
):
    mock_fetch_headlines.return_value = ["bullish"]
    mock_score_headlines.return_value = [{"score": 0.4}]
    mock_classify_regime.return_value = "recovery"
    mock_find_analogs.return_value = []

    result = MarketOrchestrator().run_cycle(
        last_candle={"price_change_pct": 1.2},
        recent_daily_candles=[{"close": 100}] * 20,
    )

    assert result.signal == "buy"


@patch("src.orchestrator.agent.find_analogs")
@patch("src.orchestrator.agent.classify_regime")
@patch("src.orchestrator.agent.score_headlines")
@patch("src.orchestrator.agent.fetch_headlines")
def test_run_cycle_emits_sell_signal_when_conditions_match(
    mock_fetch_headlines,
    mock_score_headlines,
    mock_classify_regime,
    mock_find_analogs,
):
    mock_fetch_headlines.return_value = ["bearish"]
    mock_score_headlines.return_value = [{"score": -0.5}]
    mock_classify_regime.return_value = "crisis"
    mock_find_analogs.return_value = []

    result = MarketOrchestrator().run_cycle(
        last_candle={"price_change_pct": -2.0},
        recent_daily_candles=[{"close": 100}] * 20,
    )

    assert result.signal == "sell"


@patch("src.orchestrator.agent.find_analogs")
@patch("src.orchestrator.agent.classify_regime")
@patch("src.orchestrator.agent.score_headlines")
@patch("src.orchestrator.agent.fetch_headlines")
def test_run_cycle_defaults_to_hold_when_conditions_do_not_match(
    mock_fetch_headlines,
    mock_score_headlines,
    mock_classify_regime,
    mock_find_analogs,
):
    mock_fetch_headlines.return_value = ["neutral"]
    mock_score_headlines.return_value = [{"score": 0.05}]
    mock_classify_regime.return_value = "trending_up"
    mock_find_analogs.return_value = []

    result = MarketOrchestrator().run_cycle(
        last_candle={"price_change_pct": 0.2},
        recent_daily_candles=[{"close": 100}] * 20,
    )

    assert result.signal == "hold"


@patch("src.orchestrator.agent.find_analogs")
@patch("src.orchestrator.agent.classify_regime")
@patch("src.orchestrator.agent.score_headlines")
@patch("src.orchestrator.agent.fetch_headlines")
def test_run_cycle_handles_empty_headlines_gracefully(
    mock_fetch_headlines,
    mock_score_headlines,
    mock_classify_regime,
    mock_find_analogs,
):
    mock_fetch_headlines.return_value = []
    mock_score_headlines.return_value = []
    mock_classify_regime.return_value = "baseline"
    mock_find_analogs.return_value = []

    orchestrator = MarketOrchestrator()
    result = orchestrator.run_cycle(
        last_candle={"price_change_pct": 0.0},
        recent_daily_candles=[{"close": 100}] * 20,
    )

    assert result.sentiment_score == 0.0
    assert result.signal == "hold"
    mock_score_headlines.assert_called_once_with([])
