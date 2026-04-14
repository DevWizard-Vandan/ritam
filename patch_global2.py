import sys

with open('src/agents/global_market.py', 'r') as f:
    content = f.read()

import re

search_block = """import time
import yfinance as yf
from loguru import logger
from src.agents.base import AgentBase, AgentSignal

# Global cache to persist across collection cycles
_cache: dict = {"data": None, "fetched_at": 0}
CACHE_TTL_SECONDS = 900  # 15 minutes — refresh every 3 cycles"""

replace_block = """import time
from datetime import datetime, timedelta
import yfinance as yf
from loguru import logger
from src.agents.base import AgentBase, AgentSignal
from src.config import settings

# Global cache to persist across collection cycles
_cache: dict = {}
_cache_ts: datetime | None = None
CACHE_TTL_MINUTES: int = 30"""

content = content.replace(search_block, replace_block)

search_block2 = """    def collect(self) -> dict:
        global _cache
        now = time.time()

        # Return cached data if it's still fresh
        if _cache["data"] and (now - _cache["fetched_at"]) < CACHE_TTL_SECONDS:
            logger.debug("GlobalMarketAgent: using cached data")
            return _cache["data"]

        tickers_str = " ".join(self.TICKERS.values())
        data = None

        try:
            for attempt in range(3):
                try:
                    data = yf.download(
                        tickers=tickers_str,
                        period="5d",
                        interval="1d",
                        group_by="ticker",
                        auto_adjust=True,
                        progress=False,
                        threads=False,
                    )
                    if data is not None and not data.empty:
                        break
                except Exception:
                    if attempt < 2:
                        time.sleep(2 ** attempt)
                    else:
                        raise  # Final attempt failed, move to exception handler

            if data is None or data.empty:
                raise ValueError("No data returned from yfinance")

            # Process the raw data into percentage changes
            results = {}
            for name, ticker in self.TICKERS.items():
                try:
                    close = data[ticker]["Close"].dropna()
                    if len(close) >= 2:
                        pct_change = (close.iloc[-1] - close.iloc[-2]) / close.iloc[-2] * 100
                        results[name] = round(float(pct_change), 3)
                    else:
                        results[name] = 0.0
                except KeyError:
                    results[name] = 0.0

            # Update cache on success
            _cache = {"data": results, "fetched_at": now}
            return results

        except Exception as e:
            # On rate limit or error — return last cached if available
            if _cache["data"]:
                logger.warning(
                    f"GlobalMarketAgent: rate limited or error, "
                    f"using cached data from {int((now - _cache['fetched_at'])/60)}m ago"
                )
                return _cache["data"]

            logger.error(f"GlobalMarketAgent: fetch failed and no cache available: {e}")
            return {k: 0.0 for k in self.TICKERS}"""

replace_block2 = """    def collect(self) -> dict:
        global _cache, _cache_ts
        now = datetime.now()

        # Return cached data if it's still fresh
        if _cache and _cache_ts and (now - _cache_ts) < timedelta(minutes=CACHE_TTL_MINUTES):
            logger.debug("GlobalMarketAgent: using cached data")
            return _cache

        tickers_str = " ".join(self.TICKERS.values())
        data = None

        try:
            for attempt in range(3):
                try:
                    data = yf.download(
                        tickers=tickers_str,
                        period="5d",
                        interval="1d",
                        group_by="ticker",
                        auto_adjust=True,
                        progress=False,
                        threads=False,
                    )
                    if data is not None and not data.empty:
                        break
                except Exception:
                    if attempt < 2:
                        time.sleep(2 ** attempt)
                    else:
                        raise  # Final attempt failed, move to exception handler

            if data is None or data.empty:
                raise ValueError("No data returned from yfinance")

            # Process the raw data into percentage changes
            results = {}
            for name, ticker in self.TICKERS.items():
                try:
                    close = data[ticker]["Close"].dropna()
                    if len(close) >= 2:
                        pct_change = (close.iloc[-1] - close.iloc[-2]) / close.iloc[-2] * 100
                        results[name] = round(float(pct_change), 3)
                    else:
                        results[name] = 0.0
                except KeyError:
                    results[name] = 0.0

            # Update cache on success
            _cache = results
            _cache_ts = now
            return results

        except Exception as e:
            # On rate limit or error — return last cached if available
            if _cache:
                logger.warning("yfinance rate limited — using cached data")
                return _cache
            else:
                logger.error("GlobalMarketAgent: no cache + rate limited")
                return {k: 0.0 for k in self.TICKERS}"""

if search_block2 in content:
    content = content.replace(search_block2, replace_block2)
    with open('src/agents/global_market.py', 'w') as f:
        f.write(content)
    print("Replaced global_market successfully")
else:
    print("Search block not found")
