import pytest
from src.agents.options_chain import OptionsChainAgent

def test_options_chain_pcr_bullish(monkeypatch):
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

    class MockSession:
        def __init__(self):
            self.headers = {}
        def update(self, headers):
            pass
        def get(self, url, timeout):
            return MockResponse()

    import requests
    monkeypatch.setattr(requests, "Session", MockSession)

    agent = OptionsChainAgent()
    data = agent.collect()
    assert data["pcr"] == 1.5

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

    class MockSession:
        def __init__(self):
            self.headers = {}
        def update(self, headers):
            pass
        def get(self, url, timeout):
            return MockResponse()

    import requests
    monkeypatch.setattr(requests, "Session", MockSession)

    agent = OptionsChainAgent()
    data = agent.collect()
    assert data["pcr"] == 0.5

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

    class MockSession:
        def __init__(self):
            self.headers = {}
        def update(self, headers):
            pass
        def get(self, url, timeout):
            return MockResponse()

    import requests
    monkeypatch.setattr(requests, "Session", MockSession)

    agent = OptionsChainAgent()
    data = agent.collect()
    assert data["pcr"] == 1.0

    signal = agent.reason(data)
    assert signal.signal == 0
