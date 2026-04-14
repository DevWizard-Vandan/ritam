import pytest
from unittest.mock import patch
from src.config import settings
from src.orchestrator.agent import MarketOrchestrator
from src.data.db import init_db

@pytest.fixture(autouse=True)
def mock_db_path(tmp_path, monkeypatch):
    db_file = tmp_path / "nested" / "test_market_intraday.db"
    monkeypatch.setattr(settings, "DB_PATH", str(db_file))
    init_db()
    return db_file

@patch("src.orchestrator.agent.AnalogExplainer.explain")
@patch("src.orchestrator.agent.find_analogs")
@patch("src.orchestrator.agent.classify_regime")
@patch("src.orchestrator.agent.score_headlines")
@patch("src.orchestrator.agent.fetch_headlines")
@patch("src.agents.factory.build_agents")
@patch("src.agents.factory.build_synthesis_agent")
@patch("src.data.db.log_agent_signals")
@patch("src.data.db.read_intraday_candles")
def test_orchestrator_uses_intraday_path(
    mock_read_intraday,
    mock_log,
    mock_build_synthesis_agent,
    mock_build_agents,
    mock_fetch_headlines,
    mock_score_headlines,
    mock_classify_regime,
    mock_find_analogs,
    mock_explain,
):
    settings.USE_INTRADAY = True

    mock_read_intraday.return_value = [{"close": 100}] * 15 # >= 10 candles

    from src.agents.base import AgentSignal
    mock_fetch_headlines.return_value = []
    mock_score_headlines.return_value = []
    mock_classify_regime.return_value = "baseline"
    mock_find_analogs.return_value = []
    mock_explain.return_value = "Test explanation"

    mock_build_agents.return_value = []
    class MockSynth:
        def reason(self, data):
            return AgentSignal("MacroSynthesisAgent", 1, 0.8, "bullish reason")
    mock_build_synthesis_agent.return_value = MockSynth()

    orchestrator = MarketOrchestrator(analog_top_n=2)
    result = orchestrator.run_cycle(
        last_candle={"price_change_pct": 0.5},
        recent_daily_candles=[{"close": 100}] * 20,
    )

    assert result.source == "intraday"
    assert mock_read_intraday.called


@patch("src.orchestrator.agent.AnalogExplainer.explain")
@patch("src.orchestrator.agent.find_analogs")
@patch("src.orchestrator.agent.classify_regime")
@patch("src.orchestrator.agent.score_headlines")
@patch("src.orchestrator.agent.fetch_headlines")
@patch("src.agents.factory.build_agents")
@patch("src.agents.factory.build_synthesis_agent")
@patch("src.data.db.log_agent_signals")
@patch("src.data.db.read_intraday_candles")
def test_orchestrator_falls_back_to_daily(
    mock_read_intraday,
    mock_log,
    mock_build_synthesis_agent,
    mock_build_agents,
    mock_fetch_headlines,
    mock_score_headlines,
    mock_classify_regime,
    mock_find_analogs,
    mock_explain,
):
    settings.USE_INTRADAY = True

    mock_read_intraday.return_value = [{"close": 100}] * 5 # < 10 candles -> fallback

    from src.agents.base import AgentSignal
    mock_fetch_headlines.return_value = []
    mock_score_headlines.return_value = []
    mock_classify_regime.return_value = "baseline"
    mock_find_analogs.return_value = []
    mock_explain.return_value = "Test explanation"

    mock_build_agents.return_value = []
    class MockSynth:
        def reason(self, data):
            return AgentSignal("MacroSynthesisAgent", 1, 0.8, "bullish reason")
    mock_build_synthesis_agent.return_value = MockSynth()

    orchestrator = MarketOrchestrator(analog_top_n=2)
    result = orchestrator.run_cycle(
        last_candle={"price_change_pct": 0.5},
        recent_daily_candles=[{"close": 100}] * 20,
    )

    assert result.source == "daily"
    assert mock_read_intraday.called
