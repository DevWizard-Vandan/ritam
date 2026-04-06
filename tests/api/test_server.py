"""Basic tests for FastAPI server endpoints."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch


@pytest.fixture
def client():
    with patch("src.data.db.read_candles", return_value=[]), \
         patch("src.data.db.get_connection"):
        from src.api.server import app
        return TestClient(app)


def test_accuracy_endpoint_returns_dict(client):
    with patch("src.data.db.get_connection") as mock_conn:
        mock_conn.return_value.__enter__.return_value.execute.return_value.fetchone.return_value = [0]
        resp = client.get("/api/accuracy")
        assert resp.status_code == 200
        assert "direction_accuracy" in resp.json()


def test_candles_endpoint_returns_200(client):
    with patch("src.data.db.read_candles", return_value=[]):
        resp = client.get("/api/candles")
        assert resp.status_code == 200
