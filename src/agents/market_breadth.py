from src.agents.base import AgentBase, AgentSignal
from loguru import logger

class MarketBreadthAgent(AgentBase):
    name = "MarketBreadthAgent"

    def collect(self) -> dict:
        import requests, time
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://www.nseindia.com/market-data/live-market-indices",
        })
        session.get("https://www.nseindia.com", timeout=10)
        time.sleep(1)
        resp = session.get(
            "https://www.nseindia.com/api/live-analysis-variations"
            "?index=niftyNext50",
            timeout=15
        )
        resp.raise_for_status()
        data = resp.json()

        advances = sum(
            1 for item in data.get("data", [])
            if item.get("perChange", 0) > 0
        )
        declines = sum(
            1 for item in data.get("data", [])
            if item.get("perChange", 0) < 0
        )
        unchanged = sum(
            1 for item in data.get("data", [])
            if item.get("perChange", 0) == 0
        )
        total = advances + declines + unchanged
        ad_ratio = advances / declines if declines > 0 else float("inf")

        return {
            "advances": advances, "declines": declines,
            "unchanged": unchanged, "total": total,
            "ad_ratio": round(ad_ratio, 3)
        }

    def reason(self, data: dict) -> AgentSignal:
        ad_ratio = data.get("ad_ratio", 1.0)
        advances = data.get("advances", 0)
        declines = data.get("declines", 0)

        if ad_ratio > 1.5:
            signal = 1
            conf = min(0.35 + (ad_ratio - 1.5) * 0.15, 0.80)
            reason = (f"Breadth bullish: {advances} advances vs "
                      f"{declines} declines (A/D={ad_ratio:.2f})")
        elif ad_ratio < 0.67:
            signal = -1
            conf = min(0.35 + (0.67 - ad_ratio) * 0.3, 0.80)
            reason = (f"Breadth bearish: {advances} advances vs "
                      f"{declines} declines (A/D={ad_ratio:.2f})")
        else:
            signal = 0
            conf = 0.25
            reason = (f"Breadth neutral: A/D ratio={ad_ratio:.2f}")

        return AgentSignal(
            agent_name=self.name, signal=signal,
            confidence=conf, reasoning=reason, raw_data=data
        )
