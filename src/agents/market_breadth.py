from src.agents.base import AgentBase, AgentSignal
from loguru import logger

class MarketBreadthAgent(AgentBase):
    name = "MarketBreadthAgent"

    def collect(self) -> dict:
        import requests, time, json
        fallback = {
            "advances": 0, "declines": 0, "unchanged": 0,
            "total": 0, "ad_ratio": 1.0, "available": False,
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/124.0.0.0 Safari/537.36",
            "Referer": "https://www.nseindia.com/market-data/live-market-indices",
        }
        endpoints = [
            "https://www.nseindia.com/api/live-analysis-variations?index=niftyNext50",
            "https://www.nseindia.com/api/live-analysis-variations?index=nifty50",
            "https://www.nseindia.com/api/allIndices",
        ]
        session = requests.Session()
        session.get("https://www.nseindia.com", timeout=10, headers=headers)
        time.sleep(1)

        data = None
        for endpoint in endpoints:
            try:
                resp = session.get(endpoint, timeout=15, headers=headers)
                resp.raise_for_status()
                if "application/json" not in resp.headers.get("Content-Type", ""):
                    logger.warning(
                        f"MarketBreadthAgent: non-JSON response from {endpoint}"
                    )
                    continue
                data = resp.json()
                break
            except (requests.RequestException, json.JSONDecodeError) as e:
                logger.warning(
                    f"MarketBreadthAgent: endpoint {endpoint} failed: {e}"
                )
                continue

        if data is None:
            return fallback

        items = data.get("data", [])
        advances = sum(
            1 for item in items
            if isinstance(item, dict) and item.get("perChange", 0) > 0
        )
        declines = sum(
            1 for item in items
            if isinstance(item, dict) and item.get("perChange", 0) < 0
        )
        unchanged = sum(
            1 for item in items
            if isinstance(item, dict) and item.get("perChange", 0) == 0
        )
        total = advances + declines + unchanged
        ad_ratio = advances / declines if declines > 0 else float("inf")

        return {
            "advances": advances, "declines": declines,
            "unchanged": unchanged, "total": total,
            "ad_ratio": round(ad_ratio, 3),
            "available": True,
        }

    def reason(self, data: dict) -> AgentSignal:
        if not data.get("available", True):
            return AgentSignal(
                agent_name=self.name, signal=0, confidence=0.0,
                reasoning="Market breadth data unavailable",
                raw_data=data,
            )
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
