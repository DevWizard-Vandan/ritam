from src.agents.base import AgentBase, AgentSignal
from loguru import logger

class SectorRotationAgent(AgentBase):
    name = "SectorRotationAgent"
    assigned_api_key: str = ""  # Uses Kite, not Gemini

    # Heavyweight sectors and their Kite symbols
    SECTORS = {
        "BankNifty": "NSE:NIFTY BANK",
        "IT": "NSE:NIFTY IT",
        "Auto": "NSE:NIFTY AUTO",
        "FMCG": "NSE:NIFTY FMCG",
        "Pharma": "NSE:NIFTY PHARMA",
        "Metal": "NSE:NIFTY METAL",
    }
    # Weights: Bank and IT are market cap heavyweights
    WEIGHTS = {
        "BankNifty": 0.30, "IT": 0.25, "Auto": 0.15,
        "FMCG": 0.10, "Pharma": 0.10, "Metal": 0.10
    }

    def collect(self) -> dict:
        """Uses KiteConnect quote API."""
        from src.data.kite_client import get_kite
        kite = get_kite()
        symbols = list(self.SECTORS.values())
        try:
            quotes = kite.quote(symbols)
            result = {}
            for name, sym in self.SECTORS.items():
                q = quotes.get(sym, {})
                ohlc = q.get("ohlc", {})
                last = q.get("last_price", 0)
                prev_close = ohlc.get("close", last)
                pct = ((last - prev_close) / prev_close * 100
                       if prev_close else 0.0)
                result[name] = round(pct, 3)
            return result
        except Exception as e:
            logger.warning(f"SectorRotationAgent Kite fetch failed: {e}")
            return {k: 0.0 for k in self.SECTORS}

    def reason(self, data: dict) -> AgentSignal:
        weighted_score = sum(
            data.get(k, 0) * w for k, w in self.WEIGHTS.items()
        )
        leaders_up = [k for k, v in data.items() if v > 0.3]
        leaders_dn = [k for k, v in data.items() if v < -0.3]

        if weighted_score > 0.3:
            signal = 1
            conf = min(0.30 + weighted_score * 0.1, 0.75)
            reason = (f"Sector rotation bullish (weighted={weighted_score:+.2f}%). "
                      f"Leading up: {leaders_up}")
        elif weighted_score < -0.3:
            signal = -1
            conf = min(0.30 + abs(weighted_score) * 0.1, 0.75)
            reason = (f"Sector rotation bearish (weighted={weighted_score:+.2f}%). "
                      f"Leading down: {leaders_dn}")
        else:
            signal = 0
            conf = 0.2
            reason = (f"Sector rotation neutral "
                      f"(weighted={weighted_score:+.2f}%)")

        return AgentSignal(
            agent_name=self.name, signal=signal,
            confidence=conf, reasoning=reason, raw_data=data
        )
