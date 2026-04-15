import pytest
import pandas as pd
from src.agents.global_market import GlobalMarketAgent


@pytest.fixture(autouse=True)
def reset_global_cache():
    import src.agents.global_market as gm
    gm._cache = {}
    gm._cache_ts = None

TICKERS = ["ES=F", "^N225", "^HSI", "YM=F"]


def _make_download_data(closes: dict[str, list[float]]):
    """Build a multi-ticker multi-level DataFrame mimicking yf.download output."""
    dates = pd.date_range("2024-01-01", periods=5)
    cols = pd.MultiIndex.from_product([list(closes.keys()), ["Close"]])
    data = pd.DataFrame(
        {(t, "Close"): ([0.0] * (5 - len(v)) + list(v)) for t, v in closes.items()},
        index=dates,
    )
    data.columns = pd.MultiIndex.from_tuples(data.columns)
    return data


class MockTicker:
    def __init__(self, ticker, closes):
        self.closes = closes
        self.ticker = ticker
    def history(self, **kwargs):
        import pandas as pd
        dates = pd.date_range("2024-01-01", periods=len(self.closes))
        return pd.DataFrame({"Close": self.closes}, index=dates)

def mock_yf_ticker_factory(closes_dict):
    def factory(ticker_name):
        # find matching ticker in dictionary
        return MockTicker(ticker_name, closes_dict.get(ticker_name, [100.0, 100.0]))
    return factory

def test_global_market_bullish(monkeypatch):
    import yfinance as yf
    closes = {t: [100.0, 101.0] for t in TICKERS}
    monkeypatch.setattr(yf, "Ticker", mock_yf_ticker_factory(closes))

    agent = GlobalMarketAgent()
    data = agent.collect()

    assert all(v > 0.2 for v in data.values())
    signal = agent.reason(data)
    assert signal.signal == 1


def test_global_market_bearish(monkeypatch):
    import yfinance as yf
    closes = {t: [100.0, 99.0] for t in TICKERS}
    monkeypatch.setattr(yf, "Ticker", mock_yf_ticker_factory(closes))

    agent = GlobalMarketAgent()
    data = agent.collect()

    assert all(v < -0.2 for v in data.values())
    signal = agent.reason(data)
    assert signal.signal == -1


def test_global_market_neutral(monkeypatch):
    import yfinance as yf
    closes = {
        "ES=F": [100.0, 101.0],
        "^N225": [100.0, 101.0],
        "^HSI": [100.0, 99.0],
        "YM=F": [100.0, 99.0],
    }
    monkeypatch.setattr(yf, "Ticker", mock_yf_ticker_factory(closes))

    agent = GlobalMarketAgent()
    data = agent.collect()

    signal = agent.reason(data)
    assert signal.signal == 0


def test_global_market_rate_limit_fallback(monkeypatch):
    """All yf.Ticker attempts raise → neutral fallback returned."""
    import yfinance as yf

    def raise_exc(*args, **kw):
        raise Exception("rate limited")

    monkeypatch.setattr(yf, "Ticker", raise_exc)
    # Patch time.sleep so the test doesn't actually wait
    import time
    monkeypatch.setattr(time, "sleep", lambda s: None)

    agent = GlobalMarketAgent()
    data = agent.collect()

    assert data == {k: 0.0 for k in agent.TICKERS}


def test_global_market_cache_hit(monkeypatch):
    import yfinance as yf

    agent = GlobalMarketAgent()

    # Pre-warm the cache
    from datetime import datetime
    import src.agents.global_market as gm
    gm._cache = {t: 1.0 for t in agent.TICKERS}
    gm._cache_ts = datetime.now()

    # Mock yfinance to raise an error if it's called
    def raise_exc(*args, **kw):
        raise Exception("Should not be called")

    monkeypatch.setattr(yf, "Ticker", raise_exc)

    data = agent.collect()
    assert data == gm._cache

    # Cleanup
    gm._cache = {}
    gm._cache_ts = None

def test_global_market_cache_miss_rate_limit_empty(monkeypatch):
    import yfinance as yf

    agent = GlobalMarketAgent()

    import src.agents.global_market as gm
    gm._cache = {}
    gm._cache_ts = None

    def raise_exc(*args, **kw):
        raise Exception("rate limited")

    monkeypatch.setattr(yf, "Ticker", raise_exc)
    import time
    monkeypatch.setattr(time, "sleep", lambda s: None)

    data = agent.collect()
    assert data == {k: 0.0 for k in agent.TICKERS}

def test_global_market_cache_miss_rate_limit_warm(monkeypatch):
    import yfinance as yf

    agent = GlobalMarketAgent()

    from datetime import datetime, timedelta
    import src.agents.global_market as gm

    stale_cache = {t: 2.0 for t in agent.TICKERS}
    gm._cache = stale_cache
    gm._cache_ts = datetime.now() - timedelta(minutes=40)

    def raise_exc(*args, **kw):
        raise Exception("rate limited")

    monkeypatch.setattr(yf, "Ticker", raise_exc)
    import time
    monkeypatch.setattr(time, "sleep", lambda s: None)

    data = agent.collect()
    # It should return the stale cache if yfinance fails
    assert data == stale_cache

    # Cleanup
    gm._cache = {}
    gm._cache_ts = None
