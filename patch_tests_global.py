import sys

with open('tests/agents/test_global_market.py', 'r') as f:
    content = f.read()

append_block = """

def test_global_market_cache_hit(monkeypatch):
    import yfinance as yf

    agent = GlobalMarketAgent()

    # Pre-warm the cache
    from datetime import datetime
    import src.agents.global_market as gm
    gm._cache = {t: 1.0 for t in agent.TICKERS}
    gm._cache_ts = datetime.now()

    # Mock yfinance to raise an error if it's called
    def raise_exc(**kw):
        raise Exception("Should not be called")

    monkeypatch.setattr(yf, "download", raise_exc)

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

    def raise_exc(**kw):
        raise Exception("rate limited")

    monkeypatch.setattr(yf, "download", raise_exc)
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

    def raise_exc(**kw):
        raise Exception("rate limited")

    monkeypatch.setattr(yf, "download", raise_exc)
    import time
    monkeypatch.setattr(time, "sleep", lambda s: None)

    data = agent.collect()
    # It should return the stale cache if yfinance fails
    assert data == stale_cache

    # Cleanup
    gm._cache = {}
    gm._cache_ts = None
"""

content += append_block

with open('tests/agents/test_global_market.py', 'w') as f:
    f.write(content)

print("Updated tests/agents/test_global_market.py")
