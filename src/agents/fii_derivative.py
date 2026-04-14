from src.agents.base import AgentBase, AgentSignal
from loguru import logger

class FIIDerivativeAgent(AgentBase):
    name = "FIIDerivativeAgent"

    def collect(self) -> dict:
        """Scrapes NSE FII derivative stats (published after 6 PM daily)."""
        import requests, time
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://www.nseindia.com/reports-indices-derivatives",
        })
        session.get("https://www.nseindia.com", timeout=10)
        time.sleep(1)
        resp = session.get(
            "https://www.nseindia.com/api/fiidiiTradeReact",
            timeout=15
        )
        resp.raise_for_status()
        data = resp.json()

        fii = next(
            (item for item in data if item.get("category") == "FII/FPI"),
            None
        )
        if not fii:
            return {"fii_net": 0, "available": False}

        buy_val = float(str(fii.get("buyValue", "0")).replace(",", ""))
        sell_val = float(str(fii.get("sellValue", "0")).replace(",", ""))
        net = buy_val - sell_val

        return {
            "fii_buy": buy_val,
            "fii_sell": sell_val,
            "fii_net": round(net, 2),
            "available": True
        }

    def reason(self, data: dict) -> AgentSignal:
        if not data.get("available"):
            return AgentSignal(
                agent_name=self.name, signal=0,
                confidence=0.0,
                reasoning="FII data unavailable (published post-market)",
                raw_data=data
            )
        net = data.get("fii_net", 0)
        if net > 500:
            signal, conf = 1, min(0.40 + net / 5000, 0.80)
            reason = f"FII net buyers: ₹{net:.0f}Cr — institutional inflow"
        elif net < -500:
            signal, conf = -1, min(0.40 + abs(net) / 5000, 0.80)
            reason = f"FII net sellers: ₹{net:.0f}Cr — institutional outflow"
        else:
            signal, conf = 0, 0.20
            reason = f"FII net activity muted: ₹{net:.0f}Cr"

        return AgentSignal(
            agent_name=self.name, signal=signal,
            confidence=conf, reasoning=reason, raw_data=data
        )
