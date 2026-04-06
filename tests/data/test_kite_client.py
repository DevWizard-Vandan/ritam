"""Unit tests for kite_client.py — mocks API so no real credentials needed."""
import pytest
from unittest.mock import patch, MagicMock


def test_get_client_raises_without_api_key():
    with patch("src.config.settings.KITE_API_KEY", ""):
        from src.data.kite_client import get_client
        with pytest.raises(ValueError, match="KITE_API_KEY"):
            get_client()


def test_get_client_returns_kite_instance():
    with patch("src.config.settings.KITE_API_KEY", "fake_key"), \
         patch("src.config.settings.KITE_ACCESS_TOKEN", "fake_token"), \
         patch("kiteconnect.KiteConnect") as MockKite:
        mock_instance = MagicMock()
        MockKite.return_value = mock_instance
        from importlib import reload
        import src.data.kite_client as kc
        reload(kc)
        client = kc.get_client()
        assert client is not None
