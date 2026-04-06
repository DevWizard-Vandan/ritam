"""Tests for gemma_client.py — mocks Ollama so no real server needed."""
import pytest
from unittest.mock import patch, MagicMock


def test_quick_reason_returns_string():
    with patch("src.reasoning.gemma_client._is_ollama_running", return_value=True), \
         patch("src.reasoning.gemma_client._get_ollama_client") as mock_client:
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = "trending_up"
        mock_client.return_value.chat.completions.create.return_value = mock_resp
        from src.reasoning.gemma_client import quick_reason
        result = quick_reason("What is the regime?")
        assert isinstance(result, str)
        assert result == "trending_up"


def test_falls_back_when_ollama_offline():
    with patch("src.reasoning.gemma_client._is_ollama_running", return_value=False), \
         patch("src.reasoning.gemma_client._gemini_fallback", return_value="baseline") as mock_fb:
        from src.reasoning.gemma_client import quick_reason
        result = quick_reason("test prompt")
        mock_fb.assert_called_once()
        assert result == "baseline"


def test_deep_reason_uses_large_model():
    with patch("src.reasoning.gemma_client._is_ollama_running", return_value=True), \
         patch("src.reasoning.gemma_client._get_ollama_client") as mock_client:
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = "MATCH_1: Test scenario"
        mock_client.return_value.chat.completions.create.return_value = mock_resp
        from src.reasoning.gemma_client import deep_reason, GEMMA_LARGE
        deep_reason("Find analogs")
        call_kwargs = mock_client.return_value.chat.completions.create.call_args
        assert call_kwargs.kwargs["model"] == GEMMA_LARGE
