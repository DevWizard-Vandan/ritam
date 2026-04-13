"""Tests for gemma_client.py."""
import pytest
from unittest.mock import patch, MagicMock
import src.reasoning.gemma_client
from src.config import settings

def test_quick_reason_uses_flash_lite():
    with patch("src.reasoning.gemma_client._call_flash_lite", return_value="flash_lite_result") as mock_flash_lite, \
         patch("src.reasoning.gemma_client._call_flash") as mock_flash:
        from src.reasoning.gemma_client import quick_reason
        result = quick_reason("prompt")
        assert result == "flash_lite_result"
        mock_flash_lite.assert_called_once_with("prompt")
        mock_flash.assert_not_called()

def test_deep_reason_uses_flash():
    with patch("src.reasoning.gemma_client._call_flash", return_value="flash_result") as mock_flash, \
         patch("src.reasoning.gemma_client._call_flash_lite") as mock_flash_lite:
        from src.reasoning.gemma_client import deep_reason
        result = deep_reason("prompt")
        assert result == "flash_result"
        mock_flash.assert_called_once_with("prompt")
        mock_flash_lite.assert_not_called()

def test_quick_reason_falls_back_to_flash():
    with patch("src.reasoning.gemma_client._call_flash_lite", side_effect=Exception("Failed")), \
         patch("src.reasoning.gemma_client._call_flash", return_value="fallback_flash_result") as mock_flash:
        from src.reasoning.gemma_client import quick_reason
        result = quick_reason("prompt")
        assert result == "fallback_flash_result"
        mock_flash.assert_called_once_with("prompt")

def test_deep_reason_falls_back_to_flash_lite():
    with patch("src.reasoning.gemma_client._call_flash", side_effect=Exception("Failed")), \
         patch("src.reasoning.gemma_client._call_flash_lite", return_value="fallback_flash_lite_result") as mock_flash_lite:
        from src.reasoning.gemma_client import deep_reason
        result = deep_reason("prompt")
        assert result == "fallback_flash_lite_result"
        mock_flash_lite.assert_called_once_with("prompt")

def test_quick_reason_double_fail():
    with patch("src.reasoning.gemma_client._call_flash_lite", side_effect=Exception("Failed 1")), \
         patch("src.reasoning.gemma_client._call_flash", side_effect=Exception("Failed 2")):
        from src.reasoning.gemma_client import quick_reason
        result = quick_reason("prompt")
        assert result == "baseline"

def test_deep_reason_double_fail():
    with patch("src.reasoning.gemma_client._call_flash", side_effect=Exception("Failed 1")), \
         patch("src.reasoning.gemma_client._call_flash_lite", side_effect=Exception("Failed 2")):
        from src.reasoning.gemma_client import deep_reason
        result = deep_reason("prompt")
        assert result == ""

def test_call_flash_lite_with_pro_true():
    with patch("src.reasoning.gemma_client.settings.GEMINI_USE_PRO", True), \
         patch("google.generativeai.GenerativeModel") as mock_model, \
         patch("google.generativeai.configure"):
        mock_instance = MagicMock()
        mock_instance.generate_content.return_value.text = "pro_result "
        mock_model.return_value = mock_instance
        from src.reasoning.gemma_client import _call_flash_lite
        result = _call_flash_lite("prompt")
        assert result == "pro_result"
        mock_model.assert_called_once_with(settings.GEMINI_PRO_MODEL)

def test_call_flash_with_pro_true():
    with patch("src.reasoning.gemma_client.settings.GEMINI_USE_PRO", True), \
         patch("google.generativeai.GenerativeModel") as mock_model, \
         patch("google.generativeai.configure"):
        mock_instance = MagicMock()
        mock_instance.generate_content.return_value.text = "pro_result "
        mock_model.return_value = mock_instance
        from src.reasoning.gemma_client import _call_flash
        result = _call_flash("prompt")
        assert result == "pro_result"
        mock_model.assert_called_once_with(settings.GEMINI_PRO_MODEL)

def test_call_flash_lite_with_pro_false():
    with patch("src.reasoning.gemma_client.settings.GEMINI_USE_PRO", False), \
         patch("google.generativeai.GenerativeModel") as mock_model, \
         patch("google.generativeai.configure"):
        mock_instance = MagicMock()
        mock_instance.generate_content.return_value.text = "flash_lite_result "
        mock_model.return_value = mock_instance
        from src.reasoning.gemma_client import _call_flash_lite
        result = _call_flash_lite("prompt")
        assert result == "flash_lite_result"
        mock_model.assert_called_once_with(settings.GEMINI_FLASH_LITE_MODEL)

def test_call_flash_with_pro_false():
    with patch("src.reasoning.gemma_client.settings.GEMINI_USE_PRO", False), \
         patch("google.generativeai.GenerativeModel") as mock_model, \
         patch("google.generativeai.configure"):
        mock_instance = MagicMock()
        mock_instance.generate_content.return_value.text = "flash_result "
        mock_model.return_value = mock_instance
        from src.reasoning.gemma_client import _call_flash
        result = _call_flash("prompt")
        assert result == "flash_result"
        mock_model.assert_called_once_with(settings.GEMINI_FLASH_MODEL)
