import pytest
from src.agents.options_chain import OptionsChainAgent


def _make_valid_response():
    class MockResponse:
        def json(self):
            return {
                "records": {
                    "data": [
                        {"CE": {"openInterest": 1000}, "PE": {"openInterest": 1500}, "strikePrice": 10000}
                    ],
                    "underlyingValue": 10050
                }
            }
        def raise_for_status(self): pass
        @property
        def headers(self):
            return {"Content-Type": "application/json"}
    return MockResponse()


def _make_session_class(response):
    class MockSession:
        def __init__(self):
            pass
        def get(self, url, timeout=10, headers=None):
            return response
    return MockSession


def test_options_chain_pcr_bullish(monkeypatch):
    import requests
    monkeypatch.setattr(requests, "Session", _make_session_class(_make_valid_response()))

    agent = OptionsChainAgent()
    data = agent.collect()
    assert data["pcr"] == 1.5
    assert data["available"] is True

    signal = agent.reason(data)
    assert signal.signal == 1

def test_options_chain_pcr_bearish(monkeypatch):
    class MockResponse:
        def json(self):
            return {
                "records": {
                    "data": [
                        {"CE": {"openInterest": 2000}, "PE": {"openInterest": 1000}, "strikePrice": 10000}
                    ],
                    "underlyingValue": 10050
                }
            }
        def raise_for_status(self): pass
        @property
        def headers(self):
            return {"Content-Type": "application/json"}

    import requests
    monkeypatch.setattr(requests, "Session", _make_session_class(MockResponse()))

    agent = OptionsChainAgent()
    data = agent.collect()
    assert data["pcr"] == 0.5
    assert data["available"] is True

    signal = agent.reason(data)
    assert signal.signal == -1

def test_options_chain_pcr_neutral(monkeypatch):
    class MockResponse:
        def json(self):
            return {
                "records": {
                    "data": [
                        {"CE": {"openInterest": 1000}, "PE": {"openInterest": 1000}, "strikePrice": 10000}
                    ],
                    "underlyingValue": 10050
                }
            }
        def raise_for_status(self): pass
        @property
        def headers(self):
            return {"Content-Type": "application/json"}

    import requests
    monkeypatch.setattr(requests, "Session", _make_session_class(MockResponse()))

    agent = OptionsChainAgent()
    data = agent.collect()
    assert data["pcr"] == 1.0
    assert data["available"] is True

    signal = agent.reason(data)
    assert signal.signal == 0


def test_options_chain_non_json_response_returns_fallback(monkeypatch):
    """Mock session returning a non-JSON string -> fallback with available=False."""
    class NonJsonResponse:
        def json(self):
            raise ValueError("No JSON object could be decoded")
        def raise_for_status(self): pass
        @property
        def headers(self):
            return {"Content-Type": "text/html"}

    import requests
    monkeypatch.setattr(requests, "Session", _make_session_class(NonJsonResponse()))

    agent = OptionsChainAgent()
    data = agent.collect()
    assert data["available"] is False
    assert data["pcr"] == 1.0
    assert data["max_pain"] == 0
    assert data["underlying"] == 0


def test_options_chain_reason_unavailable(monkeypatch):
    """reason() returns neutral AgentSignal when available=False."""
    agent = OptionsChainAgent()
    fallback = {
        "pcr": 1.0, "max_pain": 0, "underlying": 0,
        "total_call_oi": 0, "total_put_oi": 0, "available": False,
    }
    signal = agent.reason(fallback)
    assert signal.signal == 0
    assert signal.confidence == 0.0
    assert "unavailable" in signal.reasoning.lower()
