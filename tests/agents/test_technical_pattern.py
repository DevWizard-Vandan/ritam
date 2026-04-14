import pytest
import json
from src.agents.technical_pattern import TechnicalPatternAgent

def test_technical_pattern_valid_json(monkeypatch):
    agent = TechnicalPatternAgent()

    def mock_gemini_call(prompt, model):
        return json.dumps({
            "trend": "up",
            "pattern": "flag",
            "support": 10000,
            "resistance": 10500,
            "signal": 1,
            "confidence": 0.8,
            "reasoning": "Uptrend with flag pattern."
        })
    monkeypatch.setattr(agent, "_gemini_call", mock_gemini_call)

    # Need at least 10 candles
    candles = [{"timestamp_ist": f"2023-01-{i:02d}", "open": 100, "high": 105, "low": 95, "close": 102} for i in range(1, 15)]
    data = {"candles": candles}

    signal = agent.reason(data)
    assert signal.signal == 1
    assert signal.confidence == 0.8

def test_technical_pattern_malformed_json(monkeypatch):
    agent = TechnicalPatternAgent()

    def mock_gemini_call(prompt, model):
        return "Not a valid JSON"
    monkeypatch.setattr(agent, "_gemini_call", mock_gemini_call)

    candles = [{"timestamp_ist": f"2023-01-{i:02d}", "open": 100, "high": 105, "low": 95, "close": 102} for i in range(1, 15)]
    data = {"candles": candles}

    signal = agent.reason(data)
    assert signal.signal == 0
    assert signal.confidence == 0.1
