import os
from types import SimpleNamespace
from unittest.mock import Mock

os.environ["DB_MODE"] = "sqlite"

from src.config import settings
from src.orchestrator.agent import MarketOrchestrator


class _DummyPaperEngine:
    def __init__(self):
        self.open_pos = None
        self.open_position = Mock(side_effect=self._open_position)
        self.close_position = Mock()

    def _open_position(self, signal, price, timestamp):
        self.open_pos = {"signal": signal, "entry_price": price, "entry_time": timestamp}


class _DummyTradeTracker:
    def __init__(self, *args, **kwargs):
        self.records = []

    def record_decision(self, **kwargs):
        self.records.append(kwargs)
        return {"should_log": True, "occurrence": 1}


def _patch_common(monkeypatch):
    monkeypatch.setattr(settings, "USE_INTRADAY", False)
    monkeypatch.setattr("src.orchestrator.agent.PredictionTracker", lambda *args, **kwargs: SimpleNamespace())
    monkeypatch.setattr("src.orchestrator.agent.FeedbackLoop", lambda tracker: SimpleNamespace(record_prediction=lambda result: "2026-04-25T10:00:00+05:30"))
    monkeypatch.setattr("src.orchestrator.agent.PerformanceTracker", _DummyTradeTracker)
    monkeypatch.setattr("src.orchestrator.agent.PaperTradingEngine", _DummyPaperEngine)
    monkeypatch.setattr("src.orchestrator.agent.fetch_headlines", lambda: ["neutral"])
    monkeypatch.setattr("src.orchestrator.agent.score_headlines", lambda headlines: [{"score": 0.0}])
    monkeypatch.setattr("src.orchestrator.agent.classify_regime", lambda **kwargs: "trending_up")
    monkeypatch.setattr("src.orchestrator.agent.find_analogs", lambda *args, **kwargs: [])
    monkeypatch.setattr("src.orchestrator.agent.AnalogExplainer.explain", lambda *args, **kwargs: "test explanation")
    monkeypatch.setattr("src.data.db.log_agent_signals", lambda *args, **kwargs: None)
    monkeypatch.setattr("src.agents.factory.build_agents", lambda: [])
    monkeypatch.setattr(
        "src.agents.factory.build_synthesis_agent",
        lambda: SimpleNamespace(reason=lambda data: SimpleNamespace(agent_name="MacroSynthesisAgent", signal=1, confidence=0.8, reasoning="bullish")),
    )


def test_run_cycle_calls_trade_gate_and_executes_when_approved(monkeypatch):
    _patch_common(monkeypatch)

    gate_calls = []

    def _gate(**kwargs):
        gate_calls.append(kwargs)
        return {
            "decision": "TRADE",
            "reason_code": "TRADE_ALLOWED",
            "reason": "approved",
            "signal": "BUY_CALL",
            "details": {"confidence_original": 0.8, "confidence_adjusted": 0.8, "pcr_value": 1.0, "regime": "trending_up"},
        }

    monkeypatch.setattr("src.orchestrator.agent.evaluate_trade", _gate)

    orchestrator = MarketOrchestrator()
    result = orchestrator.run_cycle(
        last_candle={"price_change_pct": 1.2, "close": 100, "timestamp_ist": "2026-04-25T10:00:00+05:30"},
        recent_daily_candles=[{"close": 100}] * 20,
    )

    assert gate_calls
    assert gate_calls[0]["regime"] == "trending_up"
    assert result.trade_gate["decision"] == "TRADE"
    assert result.execution_action == "EXECUTE"
    assert orchestrator.paper_engine.open_position.called


def test_run_cycle_skips_execution_and_samples_no_trade(monkeypatch):
    _patch_common(monkeypatch)

    gate_calls = []

    def _gate(**kwargs):
        gate_calls.append(kwargs)
        return {
            "decision": "NO_TRADE",
            "reason_code": "PCR_EXTREME",
            "reason": "blocked",
            "signal": None,
            "details": {"confidence_original": 0.8, "confidence_adjusted": 0.7, "pcr_value": 1.7, "regime": "trending_up"},
        }

    monkeypatch.setattr("src.orchestrator.agent.evaluate_trade", _gate)

    orchestrator = MarketOrchestrator()
    result = orchestrator.run_cycle(
        last_candle={"price_change_pct": 1.2, "close": 100, "timestamp_ist": "2026-04-25T10:00:00+05:30"},
        recent_daily_candles=[{"close": 100}] * 20,
    )

    assert gate_calls
    assert result.trade_gate["decision"] == "NO_TRADE"
    assert result.execution_action == "SKIP"
    assert len(orchestrator.trade_tracker.records) == 1
    assert orchestrator.paper_engine.open_position.call_count == 0
