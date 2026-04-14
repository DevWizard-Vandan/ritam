import time
from datetime import datetime, timedelta
import yfinance as yf
from loguru import logger
from src.agents.base import AgentBase, AgentSignal
from src.config import settings

# Global cache to persist across collection cycles
_cache: dict = {}
_cache_ts: datetime | None = None
CACHE_TTL_MINUTES: int = 30

class GlobalMarketAgent(AgentBase):
    name = "GlobalMarketAgent"

    TICKERS = {
        "SP500_futures": "ES=F",
        "Nikkei": "^N225",
        "HangSeng": "^HSI",
        "DowFutures": "YM=F",
    }

    def collect(self) -> dict:
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
