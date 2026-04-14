import pytest
import json
from src.agents.market_breadth import MarketBreadthAgent


class _MockResponse:
    """Reusable mock HTTP response."""
    def __init__(self, body, content_type="application/json", status=200):
        self._body = body
        self._content_type = content_type
        self._status = status

    def raise_for_status(self):
        if self._status >= 400:
            raise Exception(f"HTTP {self._status}")

    @property
    def headers(self):
        return {"Content-Type": self._content_type}

    def json(self):
        if isinstance(self._body, str):
            raise json.JSONDecodeError("no JSON", self._body, 0)
        return self._body


def _make_session_class(url_to_response: dict):
    """Build a MockSession whose get() returns per-URL-pattern responses."""
    class MockSession:
        def __init__(self):
            pass

        def get(self, url, timeout=10, headers=None):
            if url == "https://www.nseindia.com":
                return _MockResponse({})
            for pattern, resp in url_to_response.items():
                if pattern in url:
                    return resp
            return _MockResponse({})

    return MockSession


def test_market_breadth_skips_string_items(monkeypatch):
    """collect() skips string items in data[], counts only dicts."""
    import requests, time

    good_data = {
        "data": [
            {"perChange": 1.5},   # advance
            {"perChange": -0.5},  # decline
            "some_string_item",   # should be skipped
            {"perChange": 0.0},   # unchanged
        ]
    }

    MockSession = _make_session_class(
        {"live-analysis-variations": _MockResponse(good_data)}
    )
    monkeypatch.setattr(requests, "Session", MockSession)
    monkeypatch.setattr(time, "sleep", lambda s: None)

    agent = MarketBreadthAgent()
    data = agent.collect()

    assert data["available"] is True
    assert data["advances"] == 1
    assert data["declines"] == 1
    assert data["unchanged"] == 1
    assert data["total"] == 3


def test_market_breadth_all_endpoints_non_json_returns_fallback(monkeypatch):
    """When all endpoints return non-JSON, collect() returns fallback."""
    import requests, time

    html_resp = _MockResponse("<html>error</html>", content_type="text/html")
    MockSession = _make_session_class(
        {
            "live-analysis-variations": html_resp,
            "allIndices": html_resp,
        }
    )
    monkeypatch.setattr(requests, "Session", MockSession)
    monkeypatch.setattr(time, "sleep", lambda s: None)

    agent = MarketBreadthAgent()
    data = agent.collect()

    assert data["available"] is False
    assert data["advances"] == 0
    assert data["declines"] == 0
    assert data["ad_ratio"] == 1.0


def test_market_breadth_reason_unavailable():
    """reason() returns neutral AgentSignal when available=False."""
    agent = MarketBreadthAgent()
    fallback = {
        "advances": 0, "declines": 0, "unchanged": 0,
        "total": 0, "ad_ratio": 1.0, "available": False,
    }
    signal = agent.reason(fallback)
    assert signal.signal == 0
    assert signal.confidence == 0.0
    assert "unavailable" in signal.reasoning.lower()


def test_market_breadth_bullish(monkeypatch):
    """Bullish breadth when many more advances than declines."""
    import requests, time

    good_data = {
        "data": [{"perChange": 1.0}] * 40 + [{"perChange": -1.0}] * 10
    }

    MockSession = _make_session_class(
        {"live-analysis-variations": _MockResponse(good_data)}
    )
    monkeypatch.setattr(requests, "Session", MockSession)
    monkeypatch.setattr(time, "sleep", lambda s: None)

    agent = MarketBreadthAgent()
    data = agent.collect()
    assert data["available"] is True
    signal = agent.reason(data)
    assert signal.signal == 1


def test_market_breadth_fallback_endpoint_used(monkeypatch):
    """Falls back to nifty50 endpoint if niftyNext50 returns non-JSON."""
    import requests, time

    class FallbackSession:
        def __init__(self):
            pass

        def get(self, url, timeout=10, headers=None):
            if url == "https://www.nseindia.com":
                return _MockResponse({})
            if "niftyNext50" in url:
                return _MockResponse("<html>", content_type="text/html")
            if "nifty50" in url:
                return _MockResponse(
                    {"data": [{"perChange": 2.0}, {"perChange": -0.5}]}
                )
            return _MockResponse({})

    monkeypatch.setattr(requests, "Session", FallbackSession)
    monkeypatch.setattr(time, "sleep", lambda s: None)

    agent = MarketBreadthAgent()
    data = agent.collect()
    assert data["available"] is True
    assert data["advances"] == 1
    assert data["declines"] == 1
