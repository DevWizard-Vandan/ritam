import src.config.settings
from src.config.settings import settings
settings.USE_INTRADAY = False

from unittest.mock import patch

from src.orchestrator.agent import MarketOrchestrator, OrchestratorResult


@patch("src.orchestrator.agent.AnalogExplainer.explain")
@patch("src.orchestrator.agent.find_analogs")
@patch("src.orchestrator.agent.classify_regime")
@patch("src.orchestrator.agent.score_headlines")
@patch("src.orchestrator.agent.fetch_headlines")
@patch("src.agents.factory.build_agents")
@patch("src.agents.factory.build_synthesis_agent")
@patch("src.data.db.log_agent_signals")
def test_run_cycle_returns_orchestrator_result_with_expected_fields(
    mock_log,
    mock_build_synthesis_agent,
    mock_build_agents,
    mock_fetch_headlines,
    mock_score_headlines,
    mock_classify_regime,
    mock_find_analogs,
    mock_explain,
):
    from src.agents.base import AgentSignal
    mock_fetch_headlines.return_value = ["headline 1", "headline 2"]
    mock_score_headlines.return_value = [{"score": 0.2}, {"score": 0.0}]
    mock_classify_regime.return_value = "baseline"
    mock_find_analogs.return_value = [{"start_date": "2020-01-01", "end_date": "2020-01-20", "similarity_score": 0.9, "next_5day_return": 1.5}]
    mock_explain.return_value = "Test explanation"

    mock_build_agents.return_value = []
    class MockSynth:
        def reason(self, data):
            return AgentSignal("MacroSynthesisAgent", 0, 0.5, "neutral reason")
    mock_build_synthesis_agent.return_value = MockSynth()

    orchestrator = MarketOrchestrator(analog_top_n=2)
    result = orchestrator.run_cycle(
        last_candle={"price_change_pct": 0.5},
        recent_daily_candles=[{"close": 100}] * 20,
        vix=14.5,
    )

    assert isinstance(result, OrchestratorResult)
    assert result.regime == "baseline"
    assert result.sentiment_score == 0.1
    assert result.top_analogs == [{"start_date": "2020-01-01", "end_date": "2020-01-20", "similarity_score": 0.9, "next_5day_return": 1.5}]
    assert result.signal == "hold"
    assert result.explanation == "Test explanation"


@patch("src.orchestrator.agent.AnalogExplainer.explain")
@patch("src.orchestrator.agent.find_analogs")
@patch("src.orchestrator.agent.classify_regime")
@patch("src.orchestrator.agent.score_headlines")
@patch("src.orchestrator.agent.fetch_headlines")
@patch("src.agents.factory.build_agents")
@patch("src.agents.factory.build_synthesis_agent")
@patch("src.data.db.log_agent_signals")
def test_run_cycle_emits_buy_signal_when_conditions_match(
    mock_log,
    mock_build_synthesis_agent,
    mock_build_agents,
    mock_fetch_headlines,
    mock_score_headlines,
    mock_classify_regime,
    mock_find_analogs,
    mock_explain,
):
    from src.agents.base import AgentSignal
    mock_fetch_headlines.return_value = ["bullish"]
    mock_score_headlines.return_value = [{"score": 0.4}]
    mock_classify_regime.return_value = "recovery"
    mock_find_analogs.return_value = []
    mock_explain.return_value = "Test buy explanation"

    mock_build_agents.return_value = []
    class MockSynth:
        def reason(self, data):
            return AgentSignal("MacroSynthesisAgent", 1, 0.8, "bullish reason")
    mock_build_synthesis_agent.return_value = MockSynth()

    result = MarketOrchestrator().run_cycle(
        last_candle={"price_change_pct": 1.2},
        recent_daily_candles=[{"close": 100}] * 20,
    )

    assert result.signal == "buy"


@patch("src.orchestrator.agent.AnalogExplainer.explain")
@patch("src.orchestrator.agent.find_analogs")
@patch("src.orchestrator.agent.classify_regime")
@patch("src.orchestrator.agent.score_headlines")
@patch("src.orchestrator.agent.fetch_headlines")
@patch("src.agents.factory.build_agents")
@patch("src.agents.factory.build_synthesis_agent")
@patch("src.data.db.log_agent_signals")
def test_run_cycle_emits_sell_signal_when_conditions_match(
    mock_log,
    mock_build_synthesis_agent,
    mock_build_agents,
    mock_fetch_headlines,
    mock_score_headlines,
    mock_classify_regime,
    mock_find_analogs,
    mock_explain,
):
    from src.agents.base import AgentSignal
    mock_fetch_headlines.return_value = ["bearish"]
    mock_score_headlines.return_value = [{"score": -0.5}]
    mock_classify_regime.return_value = "crisis"
    mock_find_analogs.return_value = []
    mock_explain.return_value = "Test sell explanation"

    mock_build_agents.return_value = []
    class MockSynth:
        def reason(self, data):
            return AgentSignal("MacroSynthesisAgent", -1, 0.8, "bearish reason")
    mock_build_synthesis_agent.return_value = MockSynth()

    result = MarketOrchestrator().run_cycle(
        last_candle={"price_change_pct": -2.0},
        recent_daily_candles=[{"close": 100}] * 20,
    )

    assert result.signal == "sell"


@patch("src.orchestrator.agent.AnalogExplainer.explain")
@patch("src.orchestrator.agent.find_analogs")
@patch("src.orchestrator.agent.classify_regime")
@patch("src.orchestrator.agent.score_headlines")
@patch("src.orchestrator.agent.fetch_headlines")
@patch("src.agents.factory.build_agents")
@patch("src.agents.factory.build_synthesis_agent")
@patch("src.data.db.log_agent_signals")
def test_run_cycle_defaults_to_hold_when_conditions_do_not_match(
    mock_log,
    mock_build_synthesis_agent,
    mock_build_agents,
    mock_fetch_headlines,
    mock_score_headlines,
    mock_classify_regime,
    mock_find_analogs,
    mock_explain,
):
    from src.agents.base import AgentSignal
    mock_fetch_headlines.return_value = ["neutral"]
    mock_score_headlines.return_value = [{"score": 0.05}]
    mock_classify_regime.return_value = "trending_up"
    mock_find_analogs.return_value = []
    mock_explain.return_value = "Test hold explanation"

    mock_build_agents.return_value = []
    class MockSynth:
        def reason(self, data):
            return AgentSignal("MacroSynthesisAgent", 0, 0.5, "neutral reason")
    mock_build_synthesis_agent.return_value = MockSynth()

    result = MarketOrchestrator().run_cycle(
        last_candle={"price_change_pct": 0.2},
        recent_daily_candles=[{"close": 100}] * 20,
    )

    assert result.signal == "hold"


@patch("src.orchestrator.agent.AnalogExplainer.explain")
@patch("src.orchestrator.agent.find_analogs")
@patch("src.orchestrator.agent.classify_regime")
@patch("src.orchestrator.agent.score_headlines")
@patch("src.orchestrator.agent.fetch_headlines")
@patch("src.agents.factory.build_agents")
@patch("src.agents.factory.build_synthesis_agent")
@patch("src.data.db.log_agent_signals")
def test_run_cycle_handles_empty_headlines_gracefully(
    mock_log,
    mock_build_synthesis_agent,
    mock_build_agents,
    mock_fetch_headlines,
    mock_score_headlines,
    mock_classify_regime,
    mock_find_analogs,
    mock_explain,
):
    from src.agents.base import AgentSignal
    mock_fetch_headlines.return_value = []
    mock_score_headlines.return_value = []
    mock_classify_regime.return_value = "baseline"
    mock_find_analogs.return_value = []
    mock_explain.return_value = "Test empty explanation"

    mock_build_agents.return_value = []
    class MockSynth:
        def reason(self, data):
            return AgentSignal("MacroSynthesisAgent", 0, 0.5, "neutral reason")
    mock_build_synthesis_agent.return_value = MockSynth()

    orchestrator = MarketOrchestrator()
    result = orchestrator.run_cycle(
        last_candle={"price_change_pct": 0.0},
        recent_daily_candles=[{"close": 100}] * 20,
    )

    assert result.sentiment_score == 0.0
    assert result.signal == "hold"
    mock_score_headlines.assert_called_once_with([])
