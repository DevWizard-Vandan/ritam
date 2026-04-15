from fastapi.testclient import TestClient
from src.api.server import app

client = TestClient(app)

def test_get_agents_stats():
    response = client.get("/api/agents/stats")
    assert response.status_code == 200
    data = response.json()
    assert "updated_at" in data
    assert "agents" in data
    assert isinstance(data["agents"], list)

def test_get_weights_history():
    # Pass agent as query param
    response = client.get("/api/weights/history?agent=FIIDerivativeAgent&limit=10")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_trigger_weight_update():
    response = client.post("/api/weights/update")
    assert response.status_code == 200
    data = response.json()
    assert "agents" in data
    assert "updated_at" in data
    assert "new_weights" in data
