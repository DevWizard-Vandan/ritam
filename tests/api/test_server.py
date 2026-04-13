"""Basic tests for FastAPI server endpoints."""
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def client():
    with patch("src.data.db.read_candles", return_value=[]), \
         patch("src.data.db.get_connection"):
        from src.api.server import app
        from starlette.testclient import TestClient
        return TestClient(app)


def test_accuracy_endpoint_returns_dict(client):
    mock_execute = MagicMock()
    mock_execute.fetchone.side_effect = [[10], [7]]

    with patch("src.api.server.get_connection") as mock_conn:
        mock_conn.return_value.__enter__.return_value.execute.return_value = mock_execute
        resp = client.get("/api/accuracy")

    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)


def test_feedback_accuracy_endpoint_returns_dict(client):
    with patch("src.api.server.tracker.get_accuracy_stats", return_value={"total": 0, "correct": 0}):
        resp = client.get("/api/feedback/accuracy")

    assert resp.status_code == 200
    assert resp.json() == {"total": 0, "correct": 0}


def test_candles_endpoint_returns_200(client):
    with patch("src.data.db.read_candles", return_value=[]):
        resp = client.get("/api/candles")
        assert resp.status_code == 200


def test_feedback_outcome_valid_payload_returns_200(client):
    with patch("src.api.server.tracker.record_outcome") as mock_record_outcome:
        resp = client.post(
            "/api/feedback/outcome",
            json={"timestamp": "2026-04-11T09:20:00+05:30", "actual_return_pct": 0.2},
        )

    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    mock_record_outcome.assert_called_once()


def test_feedback_outcome_unknown_timestamp_returns_404(client):
    with patch("src.api.server.tracker.record_outcome", side_effect=ValueError("No prediction found for timestamp: missing")):
        resp = client.post(
            "/api/feedback/outcome",
            json={"timestamp": "missing", "actual_return_pct": -0.1},
        )

    assert resp.status_code == 404

def test_resolve_outcome_invalid_timestamp_returns_400(client):
    resp = client.post("/api/feedback/resolve/not-a-timestamp")
    assert resp.status_code == 400

def test_resolve_outcome_missing_candles_returns_404(client, monkeypatch):
    from src.feedback import loop as fb_loop
    monkeypatch.setattr(fb_loop.FeedbackLoop, "resolve_outcome", lambda self, ts: None)
    resp = client.post("/api/feedback/resolve/2023-01-01T09:15:00+05:30")
    assert resp.status_code == 404

def test_resolve_outcome_success_returns_payload(client, monkeypatch):
    from src.feedback import loop as fb_loop
    monkeypatch.setattr(fb_loop.FeedbackLoop, "resolve_outcome", lambda self, ts: {"timestamp": ts, "actual_return_pct": 1.5})
    resp = client.post("/api/feedback/resolve/2024-01-02T09:15:00+05:30")
    assert resp.status_code == 200
    assert "actual_return_pct" in resp.json()

def test_get_learning_weights_returns_200(client, monkeypatch):
    from src.learning import weight_updater as wu
    monkeypatch.setattr(wu.WeightUpdater, "get_current_weights", lambda self: {"weights": {"buy": 1.0, "sell": 1.0, "hold": 1.0}})
    resp = client.get("/api/learning/weights")
    assert resp.status_code == 200
    assert "weights" in resp.json()

def test_post_update_weights_returns_200(client, monkeypatch):
    from src.learning import weight_updater as wu
    monkeypatch.setattr(wu.WeightUpdater, "update_weights", lambda self: {"buy": {"old_weight": 1.0, "new_weight": 1.05, "accuracy_pct": 70.0}})
    resp = client.post("/api/learning/update-weights")
    assert resp.status_code == 200
    assert "buy" in resp.json()


def test_get_analogs_returns_list(client, monkeypatch):
    from src.reasoning.analog_finder import AnalogFinder
    import src.api.server
    mock_analogs = [{"start_date": "2023-01-01", "end_date": "2023-01-10", "similarity_score": 0.99, "next_5day_return": 1.5}] * 3
    monkeypatch.setattr(AnalogFinder, "find_analogs", lambda self, candles, top_n, symbol="NSE:NIFTY 50": mock_analogs)
    monkeypatch.setattr(src.api.server, "read_candles", lambda *args, **kwargs: [{"close": 100}] * 20)

    resp = client.get("/api/analogs?top_n=3")

    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert len(resp.json()) == 3
