import pytest
from unittest.mock import patch, MagicMock
from src.agents.base import AgentBase, AgentSignal
from typing import Any

class DummyAgent(AgentBase):
    name = "DummyAgent"
    assigned_api_key = "key1"

    def collect(self) -> dict[str, Any]:
        return {"data": 123}

    def reason(self, data: dict[str, Any]) -> AgentSignal:
        return AgentSignal(agent_name=self.name, signal=1, confidence=0.9, reasoning="looks good")

def test_agent_signal_dataclass():
    signal = AgentSignal(agent_name="Test", signal=-1, confidence=0.5, reasoning="bad")
    assert signal.agent_name == "Test"
    assert signal.signal == -1
    assert signal.confidence == 0.5
    assert signal.reasoning == "bad"
    assert signal.raw_data == {}

@patch("src.agents.base.genai.GenerativeModel")
@patch("src.agents.base.genai.configure")
def test_agent_base_gemini_call_success(mock_configure, mock_model_class):
    agent = DummyAgent()

    mock_model = MagicMock()
    mock_model.generate_content.return_value = MagicMock(text="response text")
    mock_model_class.return_value = mock_model

    with patch("src.config.settings.settings.GEMINI_API_KEY_7", "key7"):
        result = agent._gemini_call("prompt", "model")

    assert result == "response text"
    mock_configure.assert_called_once_with(api_key="key1")

@patch("src.agents.base.genai.GenerativeModel")
@patch("src.agents.base.genai.configure")
def test_agent_base_gemini_call_fallback(mock_configure, mock_model_class):
    agent = DummyAgent()

    mock_model = MagicMock()

    # First call raises an exception, second call succeeds
    def generate_content_side_effect(prompt):
        if mock_configure.call_args[1].get("api_key") == "key1":
            raise Exception("Key 1 failed")
        return MagicMock(text="fallback text")

    mock_model.generate_content.side_effect = generate_content_side_effect
    mock_model_class.return_value = mock_model

    with patch("src.config.settings.settings.GEMINI_API_KEY_7", "key7"):
        result = agent._gemini_call("prompt", "model")

    assert result == "fallback text"
    assert mock_configure.call_count == 2
    mock_configure.assert_any_call(api_key="key7")

@patch("src.agents.base.genai.GenerativeModel")
@patch("src.agents.base.genai.configure")
def test_agent_base_gemini_call_all_fail(mock_configure, mock_model_class):
    agent = DummyAgent()

    mock_model = MagicMock()
    mock_model.generate_content.side_effect = Exception("Failed")
    mock_model_class.return_value = mock_model

    with patch("src.config.settings.settings.GEMINI_API_KEY_7", "key7"):
        result = agent._gemini_call("prompt", "model")

    assert result == ""
    assert mock_configure.call_count == 2

def test_agent_run_success():
    agent = DummyAgent()
    signal = agent.run()

    assert signal.signal == 1
    assert signal.confidence == 0.9

def test_agent_run_exception():
    class FailingAgent(DummyAgent):
        def reason(self, data):
            raise ValueError("Something broke")

    agent = FailingAgent()
    signal = agent.run()

    assert signal.signal == 0
    assert signal.confidence == 0.0
    assert "Agent failed: Something broke" in signal.reasoning
