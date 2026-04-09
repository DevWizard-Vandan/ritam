"""Basic tests for FastAPI server endpoints."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


@pytest.fixture
def client():
    with patch("src.data.db.read_candles", return_value=[]), \
         patch("src.data.db.get_connection"):
        from src.api.server import app
        from fastapi.testclient import TestClient
        return TestClient(app)


def test_accuracy_endpoint_returns_dict(client):
    mock_execute = MagicMock()
    # First call → total=10, Second call → correct=7
    mock_execute.fetchone.side_effect = [[10], [7]]

    with patch("src.api.server.get_connection") as mock_conn:
        mock_conn.return_value.__enter__.return_value.execute.return_value = mock_execute
        resp = client.get("/api/accuracy")

    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)

def test_candles_endpoint_returns_200(client):
    with patch("src.data.db.read_candles", return_value=[]):
        resp = client.get("/api/candles")
        assert resp.status_code == 200
