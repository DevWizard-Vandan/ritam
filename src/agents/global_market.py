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
        results = {}
        for name, ticker in self.TICKERS.items():
            try:
                t = yf.Ticker(ticker)
                hist = t.history(period="2d", interval="1d")
                if len(hist) >= 2:
                    prev_close = hist["Close"].iloc[-2]
                    last_close = hist["Close"].iloc[-1]
                    pct_change = (last_close - prev_close) / prev_close * 100
                    results[name] = round(pct_change, 3)
                else:
                    results[name] = 0.0
            except Exception as e:
                logger.warning(f"GlobalMarketAgent: {ticker} failed: {e}")
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
