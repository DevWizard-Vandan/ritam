"""Tests for gemma_client.py — mocks Ollama so no real server needed."""
import pytest
from unittest.mock import patch, MagicMock


def test_quick_reason_returns_string():
    with patch("src.reasoning.gemma_client._is_ollama_running", return_value=True), \
         patch("src.reasoning.gemma_client.requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": "choppy"}
        mock_post.return_value = mock_resp
        from src.reasoning.gemma_client import quick_reason
        result = quick_reason("What is the regime?")
        assert isinstance(result, str)
        assert result == "choppy"


def test_quick_reason_fallback_chain_thinking():
    with patch("src.reasoning.gemma_client._is_ollama_running", return_value=True), \
         patch("src.reasoning.gemma_client.requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": "", "thinking": "trending_up"}
        mock_post.return_value = mock_resp
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
         patch("src.reasoning.gemma_client.requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": "MATCH_1: Test scenario"}
        mock_post.return_value = mock_resp
        from src.reasoning.gemma_client import deep_reason, GEMMA_LARGE
        deep_reason("Find analogs")
        call_kwargs = mock_post.call_args
        assert call_kwargs.kwargs["json"]["model"] == GEMMA_LARGE
