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

@patch("src.agents.base.genai.GenerativeModel")
@patch("src.agents.base.genai.configure")
@patch("time.sleep")
def test_gemini_call_429_retry_success(mock_sleep, mock_configure, mock_model_class):
    agent = DummyAgent()
    mock_model = MagicMock()

    # First attempt fails with 429 and retry_delay
    # Second attempt succeeds
    def generate_content_side_effect(*args, **kwargs):
        if mock_model.generate_content.call_count == 1:
            raise Exception("Resource has been exhausted (e.g. check quota). retry_delay { seconds: 12 }")
        return MagicMock(text="retried successfully")

    mock_model.generate_content.side_effect = generate_content_side_effect
    mock_model_class.return_value = mock_model

    with patch("src.config.settings.GEMINI_API_KEY_7", "key7"):
        result = agent._gemini_call("prompt", "model")

    assert result == "retried successfully"
    # Sleep should be called with 12 + 1 = 13
    mock_sleep.assert_called_once_with(13)
    assert mock_model.generate_content.call_count == 2
    # Configure should be called twice with "key1" because it's retrying on the SAME key
    mock_configure.assert_called_with(api_key="key1")

@patch("src.agents.base.genai.GenerativeModel")
@patch("src.agents.base.genai.configure")
@patch("time.sleep")
def test_gemini_call_429_exhausted(mock_sleep, mock_configure, mock_model_class):
    agent = DummyAgent()
    mock_model = MagicMock()

    # Every attempt fails with 429
    def generate_content_side_effect(*args, **kwargs):
        raise Exception("Resource has been exhausted. retry_delay { seconds: 5 }")

    mock_model.generate_content.side_effect = generate_content_side_effect
    mock_model_class.return_value = mock_model

    with patch("src.config.settings.GEMINI_API_KEY_7", "key7"):
        result = agent._gemini_call("prompt", "model")

    assert result == ""
    # Should sleep once for key1, once for key7
    assert mock_sleep.call_count == 2
    mock_sleep.assert_any_call(6)

@patch("src.agents.base.genai.GenerativeModel")
@patch("src.agents.base.genai.configure")
@patch("time.sleep")
def test_gemini_call_success_on_key7_after_key1_fails(mock_sleep, mock_configure, mock_model_class):
    agent = DummyAgent()
    mock_model = MagicMock()

    # First attempt fails with generic error (not 429) -> moves to key 7
    # Key 7 succeeds
    def generate_content_side_effect(*args, **kwargs):
        if mock_configure.call_args[1].get("api_key") == "key1":
            raise Exception("Some other error")
        return MagicMock(text="key7 success")

    mock_model.generate_content.side_effect = generate_content_side_effect
    mock_model_class.return_value = mock_model

    with patch("src.config.settings.GEMINI_API_KEY_7", "key7"):
        result = agent._gemini_call("prompt", "model")

    assert result == "key7 success"
    assert mock_sleep.call_count == 0
    # Should be configured with key7
    mock_configure.assert_called_with(api_key="key7")
