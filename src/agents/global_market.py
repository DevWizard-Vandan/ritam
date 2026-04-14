from src.agents.base import AgentBase, AgentSignal
from loguru import logger

class GlobalMarketAgent(AgentBase):
    name = "GlobalMarketAgent"

    TICKERS = {
        "SP500_futures": "ES=F",
        "Nikkei": "^N225",
        "HangSeng": "^HSI",
        "DowFutures": "YM=F",
    }

    def collect(self) -> dict:
        import yfinance as yf
        import time
        tickers_str = " ".join(self.TICKERS.values())

        data = None
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
                break
            except Exception as e:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                else:
                    logger.warning(
                        "GlobalMarketAgent: yfinance rate-limited, using neutral"
                    )
                    return {k: 0.0 for k in self.TICKERS}

        if data is None or data.empty:
            logger.warning("GlobalMarketAgent: yfinance rate-limited, using neutral")
            return {k: 0.0 for k in self.TICKERS}

        results = {}
        for name, ticker in self.TICKERS.items():
            try:
                close = data[ticker]["Close"].dropna()
                if len(close) >= 2:
                    pct_change = (
                        (close.iloc[-1] - close.iloc[-2]) / close.iloc[-2] * 100
                    )
                    results[name] = round(float(pct_change), 3)
                else:
                    results[name] = 0.0
            except KeyError:
                results[name] = 0.0
        return results

    def reason(self, data: dict) -> AgentSignal:
        positives = sum(1 for v in data.values() if v > 0.2)
        negatives = sum(1 for v in data.values() if v < -0.2)
        total = len(data)

        if positives >= 3:
            signal = 1
            conf = 0.35 + (positives / total) * 0.3
            reason = (f"Global markets bullish: "
                      f"{positives}/{total} up. "
                      f"SP500f={data.get('SP500_futures',0):+.2f}%")
        elif negatives >= 3:
            signal = -1
            conf = 0.35 + (negatives / total) * 0.3
            reason = (f"Global markets bearish: "
                      f"{negatives}/{total} down. "
                      f"SP500f={data.get('SP500_futures',0):+.2f}%")
        else:
            signal = 0
            conf = 0.2
            reason = f"Global markets mixed. Changes: {data}"

        return AgentSignal(
            agent_name=self.name, signal=signal,
            confidence=conf, reasoning=reason, raw_data=data
        )
