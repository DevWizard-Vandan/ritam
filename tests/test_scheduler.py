import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import datetime as dt

import src.api.server
from src.api.server import app, run_scheduled_cycle, resolve_outcomes_job, weight_update_job, scheduler_job_status
from src.config import settings

@pytest.fixture
def test_client():
    with TestClient(app) as client:
        yield client

@pytest.fixture(autouse=True)
def reset_status():
    scheduler_job_status.clear()
    yield
    scheduler_job_status.clear()

def test_scheduler_status_endpoint_enabled(test_client):
    with patch("src.api.server.settings.SCHEDULER_ENABLED", True):
        # The scheduler gets started during app startup if SCHEDULER_ENABLED is True,
        # but in test we can mock get_jobs
        with patch("src.api.server.scheduler.get_jobs") as mock_get_jobs:
            job1 = MagicMock()
            job1.id = "market_cycle"
            job1.name = "Market Cycle Job"
            job1.next_run_time = dt.datetime(2026, 4, 14, 9, 15, tzinfo=dt.timezone(dt.timedelta(hours=5, minutes=30)))

            mock_get_jobs.return_value = [job1]

            scheduler_job_status["market_cycle"] = "success"

            response = test_client.get("/api/scheduler/status")
            assert response.status_code == 200
            data = response.json()

            assert data["scheduler_enabled"] is True
            assert len(data["jobs"]) == 1
            assert data["jobs"][0]["id"] == "market_cycle"
            assert data["jobs"][0]["last_status"] == "success"
            assert data["jobs"][0]["next_run_time"] == "2026-04-14T09:15:00+05:30"

def test_scheduler_status_endpoint_disabled(test_client):
    with patch("src.api.server.settings.SCHEDULER_ENABLED", False):
        response = test_client.get("/api/scheduler/status")
        assert response.status_code == 200
        data = response.json()
        assert data["scheduler_enabled"] is False
        assert len(data["jobs"]) == 0

@patch("src.api.server.logger")
def test_run_scheduled_cycle_outside_market_hours(mock_logger):
    # Mock time to be outside market hours (e.g., 20:00)
    mock_now = dt.datetime(2026, 4, 14, 20, 0, tzinfo=dt.timezone(dt.timedelta(hours=5, minutes=30)))
    class MockDatetimeBase(dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return mock_now

    with patch("src.api.server.dt.datetime", MockDatetimeBase):
        run_scheduled_cycle()

        mock_logger.info.assert_any_call("Market closed — skipping cycle")
        assert scheduler_job_status["market_cycle"] == "skipped"

@patch("src.api.server.logger")
def test_run_scheduled_cycle_weekend(mock_logger):
    # Mock time to be a Saturday
    mock_now = dt.datetime(2026, 4, 18, 10, 0, tzinfo=dt.timezone(dt.timedelta(hours=5, minutes=30)))
    class MockDatetimeBase(dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return mock_now

    with patch("src.api.server.dt.datetime", MockDatetimeBase):
        run_scheduled_cycle()

        mock_logger.info.assert_any_call("Market closed — skipping cycle")
        assert scheduler_job_status["market_cycle"] == "skipped"

@patch("src.api.server.read_candles")
@patch("src.orchestrator.agent.MarketOrchestrator")
def test_run_scheduled_cycle_inside_market_hours(mock_orchestrator_class, mock_read_candles):
    # Mock time to be inside market hours on a weekday
    mock_now = dt.datetime(2026, 4, 14, 10, 0, tzinfo=dt.timezone(dt.timedelta(hours=5, minutes=30)))
    class MockDatetimeBase(dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return mock_now

    with patch("src.api.server.dt.datetime", MockDatetimeBase):
        mock_read_candles.return_value = [{"close": 100}] * 60

        mock_instance = MagicMock()
        mock_instance.run_cycle.return_value = MagicMock(signal="buy", regime="bull", sentiment_score=0.8)
        mock_orchestrator_class.return_value = mock_instance

        # Ensure we patch the import inside src.api.server
        with patch("src.api.server.MarketOrchestrator", mock_orchestrator_class, create=True):
            with patch("src.data.db.read_candles", mock_read_candles):
                run_scheduled_cycle()

        assert scheduler_job_status["market_cycle"] == "success"
        mock_instance.run_cycle.assert_called_once()
