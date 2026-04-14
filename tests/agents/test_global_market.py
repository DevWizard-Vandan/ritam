import pytest
import pandas as pd
from src.agents.global_market import GlobalMarketAgent

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


def test_global_market_bullish(monkeypatch):
    import yfinance as yf

    mock_data = _make_download_data({t: [100.0, 101.0] for t in TICKERS})
    monkeypatch.setattr(yf, "download", lambda **kw: mock_data)

    agent = GlobalMarketAgent()
    data = agent.collect()

    assert all(v > 0.2 for v in data.values())
    signal = agent.reason(data)
    assert signal.signal == 1


def test_global_market_bearish(monkeypatch):
    import yfinance as yf

    mock_data = _make_download_data({t: [100.0, 99.0] for t in TICKERS})
    monkeypatch.setattr(yf, "download", lambda **kw: mock_data)

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
    mock_data = _make_download_data(closes)
    monkeypatch.setattr(yf, "download", lambda **kw: mock_data)

    agent = GlobalMarketAgent()
    data = agent.collect()

    signal = agent.reason(data)
    assert signal.signal == 0


def test_global_market_rate_limit_fallback(monkeypatch):
    """All yf.download attempts raise → neutral fallback returned."""
    import yfinance as yf

    def raise_exc(**kw):
        raise Exception("rate limited")

    monkeypatch.setattr(yf, "download", raise_exc)
    # Patch time.sleep so the test doesn't actually wait
    import time
    monkeypatch.setattr(time, "sleep", lambda s: None)

    agent = GlobalMarketAgent()
    data = agent.collect()

    assert data == {k: 0.0 for k in agent.TICKERS}
