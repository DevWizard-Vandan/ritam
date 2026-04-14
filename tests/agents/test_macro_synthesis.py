import pytest
import json
from src.agents.macro_synthesis import MacroSynthesisAgent
from src.agents.base import AgentSignal

def test_macro_synthesis_bullish(monkeypatch):
    agent = MacroSynthesisAgent()

    def mock_gemini_call(prompt, model):
        return json.dumps({
            "signal": 1,
            "confidence": 0.8,
            "dominant_theme": "Bullish trend",
            "dissenting_agents": [],
            "reasoning": "Strong bullish signals."
        })
    monkeypatch.setattr(agent, "_gemini_call", mock_gemini_call)

    data = {
        "agent_signals": [
            AgentSignal("A1", 1, 0.9, "bullish"),
            AgentSignal("A2", 1, 0.8, "bullish"),
            AgentSignal("A3", 1, 0.7, "bullish"),
        ],
        "regime": "trending_up",
        "analog_summary": "good"
    }

    signal = agent.reason(data)
    assert signal.signal == 1
    assert signal.confidence == 0.8

def test_macro_synthesis_crisis(monkeypatch):
    agent = MacroSynthesisAgent()

    def mock_gemini_call(prompt, model):
        return json.dumps({
            "signal": -1,
            "confidence": 0.9,
            "dominant_theme": "Crisis",
            "dissenting_agents": [],
            "reasoning": "Crisis override."
        })
    monkeypatch.setattr(agent, "_gemini_call", mock_gemini_call)

    data = {
        "agent_signals": [
            AgentSignal("A1", -1, 0.9, "bearish"),
        ],
        "regime": "crisis",
        "analog_summary": "bad"
    }

    signal = agent.reason(data)
    assert signal.signal == -1
    assert signal.confidence == 0.9

def test_macro_synthesis_economic_calendar_uncertainty(monkeypatch):
    agent = MacroSynthesisAgent()

    def mock_gemini_call(prompt, model):
        return json.dumps({
            "signal": 1,
            "confidence": 0.4, # reduced confidence
            "dominant_theme": "Uncertain",
            "dissenting_agents": [],
            "reasoning": "Uncertain."
        })
    monkeypatch.setattr(agent, "_gemini_call", mock_gemini_call)

    data = {
        "agent_signals": [
            AgentSignal("EconomicCalendarAgent", 0, 0.2, "Uncertainty due to upcoming event"),
            AgentSignal("A2", 1, 0.8, "bullish"),
        ],
        "regime": "choppy",
        "analog_summary": "mixed"
    }

    signal = agent.reason(data)
    assert signal.signal == 1
    assert signal.confidence == 0.4
