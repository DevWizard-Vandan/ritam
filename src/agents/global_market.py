from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from datetime import datetime, timedelta
import yfinance as yf
from loguru import logger
from src.agents.base import AgentBase, AgentSignal
from src.config import settings

# Global cache to persist across collection cycles
_cache: dict = {}
_cache_ts: datetime | None = None
CACHE_TTL_MINUTES: int = 30

_BATCH_TIMEOUT_SECONDS: int = 5    # total budget for all tickers


class GlobalMarketAgent(AgentBase):
    name = "GlobalMarketAgent"

    TICKERS = {
        "SP500_futures": "ES=F",
        "Nikkei": "^N225",
        "HangSeng": "^HSI",
        "DowFutures": "YM=F",
    }

    def _fetch_one(self, name: str, ticker: str) -> tuple[str, float]:
        """Fetch a single ticker's daily % change."""
        t = yf.Ticker(ticker)
        hist = t.history(period="2d", interval="1d")
        if len(hist) >= 2:
            prev = hist["Close"].iloc[-2]
            last = hist["Close"].iloc[-1]
            return name, round((last - prev) / prev * 100, 3)
        return name, 0.0

    def collect(self) -> dict:
        global _cache, _cache_ts
        now = datetime.now()

        # Return cached data if it's still fresh
        if _cache and _cache_ts and (now - _cache_ts) < timedelta(minutes=CACHE_TTL_MINUTES):
            logger.debug("GlobalMarketAgent: using cached data")
            return _cache

        results: dict[str, float] = {}

        try:
            with ThreadPoolExecutor(max_workers=4) as ex:
                futs = {
                    ex.submit(self._fetch_one, name, ticker): name
                    for name, ticker in self.TICKERS.items()
                }
                try:
                    for fut in as_completed(futs, timeout=_BATCH_TIMEOUT_SECONDS):
                        name = futs[fut]
                        try:
                            fetched_name, val = fut.result()
                            results[fetched_name] = val
                        except Exception:
                            results[name] = 0.0
                except TimeoutError:
                    logger.warning("GlobalMarketAgent: yfinance batch timeout")
                    for name in self.TICKERS:
                        results.setdefault(name, 0.0)

            # Fill any tickers that didn't complete
            for name in self.TICKERS:
                results.setdefault(name, 0.0)

            # Update module-level cache if we got real data
            if any(v != 0.0 for v in results.values()):
                _cache = results
                _cache_ts = now

            return results

        except Exception as e:
            logger.error(f"GlobalMarketAgent: unexpected error: {e}")
            if _cache:
                logger.warning("GlobalMarketAgent: falling back to cache")
                return _cache
            return {k: 0.0 for k in self.TICKERS}

    def reason(self, data: dict) -> AgentSignal:
        positives = sum(1 for v in data.values() if v > 0.2)
        negatives = sum(1 for v in data.values() if v < -0.2)
        total = len(data)

        if positives >= 3:
            signal = 1
            conf = 0.35 + (positives / total) * 0.3
            reason = (f"Global markets bullish: {positives}/{total} up. "
                      f"SP500f={data.get('SP500_futures',0):+.2f}%")
        elif negatives >= 3:
            signal = -1
            conf = 0.35 + (negatives / total) * 0.3
            reason = (f"Global markets bearish: {negatives}/{total} down. "
                      f"SP500f={data.get('SP500_futures',0):+.2f}%")
        else:
            signal = 0
            conf = 0.2
            reason = f"Global markets mixed. Changes: {data}"

        return AgentSignal(
            agent_name=self.name, signal=signal,
            confidence=conf, reasoning=reason, raw_data=data
        )
