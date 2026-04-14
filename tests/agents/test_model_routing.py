import pytest
from unittest.mock import patch
from src.agents.base import AgentBase, AgentSignal
from src.agents.news_impact import NewsImpactAgent
from src.agents.macro_synthesis import MacroSynthesisAgent


class _DummyAgent(AgentBase):
    name = "DummyAgent"

    def collect(self):
        return {}

    def reason(self, data):
        return AgentSignal(agent_name=self.name, signal=0, confidence=0.5, reasoning="")


def test_force_flash_lite_overrides_model(monkeypatch):
    """GEMINI_FORCE_FLASH_LITE=True → _gemini_call uses Flash-Lite regardless."""
    from src.config import settings
    monkeypatch.setattr(settings, "GEMINI_FORCE_FLASH_LITE", True)
    monkeypatch.setattr(settings, "GEMINI_FLASH_LITE_MODEL", "gemini-2.5-flash-lite")

    agent = _DummyAgent()
    agent.assigned_api_key = "test-key"

    captured = {}

    import google.generativeai as genai

    class _FakeModel:
        def __init__(self, name):
            captured["model"] = name

        def generate_content(self, prompt):
            class R:
                text = '{"signal": 0}'
            return R()

    monkeypatch.setattr(genai, "configure", lambda api_key: None)
    monkeypatch.setattr(genai, "GenerativeModel", _FakeModel)

    agent._gemini_call("test prompt", "gemini-2.5-pro")
    assert captured["model"] == "gemini-2.5-flash-lite"


def test_flash_lite_not_forced_when_disabled(monkeypatch):
    """GEMINI_FORCE_FLASH_LITE=False → model_name passed through unchanged."""
    from src.config import settings
    monkeypatch.setattr(settings, "GEMINI_FORCE_FLASH_LITE", False)
    monkeypatch.setattr(settings, "GEMINI_FLASH_LITE_MODEL", "gemini-2.5-flash-lite")

    agent = _DummyAgent()
    agent.assigned_api_key = "test-key"

    captured = {}

    import google.generativeai as genai

    class _FakeModel:
        def __init__(self, name):
            captured["model"] = name

        def generate_content(self, prompt):
            class R:
                text = '{"signal": 0}'
            return R()

    monkeypatch.setattr(genai, "configure", lambda api_key: None)
    monkeypatch.setattr(genai, "GenerativeModel", _FakeModel)

    agent._gemini_call("test prompt", "gemini-2.5-pro")
    assert captured["model"] == "gemini-2.5-pro"


def test_news_impact_agent_selects_flash_lite(monkeypatch):
    """NewsImpactAgent.reason() selects Flash-Lite model when GEMINI_USE_PRO=False."""
    from src.config import settings
    monkeypatch.setattr(settings, "GEMINI_USE_PRO", False)
    monkeypatch.setattr(settings, "GEMINI_FLASH_LITE_MODEL", "gemini-2.5-flash-lite")

    agent = NewsImpactAgent()
    called_with = {}

    def mock_gemini_call(prompt, model):
        called_with["model"] = model
        import json
        return json.dumps({"signal": 0, "confidence": 0.5, "reasoning": "ok",
                           "top_theme": "t", "impact": "neutral", "key_headline": "h"})

    monkeypatch.setattr(agent, "_gemini_call", mock_gemini_call)

    data = {"headlines": ["Headline one", "Headline two"], "sentiment_score": 0.1}
    agent.reason(data)
    assert called_with["model"] == "gemini-2.5-flash-lite"


def test_macro_synthesis_agent_selects_flash_lite(monkeypatch):
    """MacroSynthesisAgent.reason() selects Flash-Lite model when GEMINI_USE_PRO=False."""
    from src.config import settings
    monkeypatch.setattr(settings, "GEMINI_USE_PRO", False)
    monkeypatch.setattr(settings, "GEMINI_FLASH_LITE_MODEL", "gemini-2.5-flash-lite")

    agent = MacroSynthesisAgent()
    called_with = {}

    def mock_gemini_call(prompt, model):
        called_with["model"] = model
        import json
        return json.dumps({"signal": 0, "confidence": 0.5, "reasoning": "ok",
                           "dominant_theme": "t", "dissenting_agents": []})

    monkeypatch.setattr(agent, "_gemini_call", mock_gemini_call)

    data = {
        "agent_signals": [AgentSignal("A", 1, 0.8, "bullish")],
        "regime": "trending_up",
        "analog_summary": "good",
    }
    agent.reason(data)
    assert called_with["model"] == "gemini-2.5-flash-lite"
