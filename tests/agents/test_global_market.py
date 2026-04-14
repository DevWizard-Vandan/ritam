import pytest
import pandas as pd
from src.agents.global_market import GlobalMarketAgent

class MockTickerPos:
    def __init__(self, ticker):
        self.ticker = ticker
    def history(self, period, interval):
        return pd.DataFrame({"Close": [100.0, 101.0]})

class MockTickerNeg:
    def __init__(self, ticker):
        self.ticker = ticker
    def history(self, period, interval):
        return pd.DataFrame({"Close": [100.0, 99.0]})

class MockTickerMixed:
    def __init__(self, ticker):
        self.ticker = ticker
    def history(self, period, interval):
        if self.ticker in ["ES=F", "^N225"]:
            return pd.DataFrame({"Close": [100.0, 101.0]})
        else:
            return pd.DataFrame({"Close": [100.0, 99.0]})

def test_global_market_bullish(monkeypatch):
    import yfinance as yf
    monkeypatch.setattr(yf, "Ticker", MockTickerPos)

    agent = GlobalMarketAgent()
    data = agent.collect()

    # 4 positive changes
    assert all(v > 0.2 for v in data.values())

    signal = agent.reason(data)
    assert signal.signal == 1

def test_global_market_bearish(monkeypatch):
    import yfinance as yf
    monkeypatch.setattr(yf, "Ticker", MockTickerNeg)

    agent = GlobalMarketAgent()
    data = agent.collect()

    # 4 negative changes
    assert all(v < -0.2 for v in data.values())

    signal = agent.reason(data)
    assert signal.signal == -1

def test_global_market_neutral(monkeypatch):
    import yfinance as yf
    monkeypatch.setattr(yf, "Ticker", MockTickerMixed)

    agent = GlobalMarketAgent()
    data = agent.collect()

    signal = agent.reason(data)
    assert signal.signal == 0
