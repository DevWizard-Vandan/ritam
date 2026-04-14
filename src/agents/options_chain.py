from src.agents.base import AgentBase, AgentSignal
from loguru import logger

class OptionsChainAgent(AgentBase):
    name = "OptionsChainAgent"
    # No API key needed — pure calculation

    def collect(self) -> dict:
        """Scrapes NSE options chain for NIFTY."""
        import requests, time
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.nseindia.com/option-chain",
        })
        # Warm up session cookie
        session.get("https://www.nseindia.com", timeout=10)
        time.sleep(1)
        resp = session.get(
            "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY",
            timeout=15
        )
        resp.raise_for_status()
        data = resp.json()
        records = data["records"]["data"]

        total_call_oi = sum(
            r["CE"]["openInterest"] for r in records if "CE" in r
        )
        total_put_oi = sum(
            r["PE"]["openInterest"] for r in records if "PE" in r
        )
        pcr = total_put_oi / total_call_oi if total_call_oi > 0 else 1.0

        # Max pain: strike where total OI loss for writers is maximum
        strikes = {}
        for r in records:
            strike = r.get("strikePrice", 0)
            ce_oi = r.get("CE", {}).get("openInterest", 0)
            pe_oi = r.get("PE", {}).get("openInterest", 0)
            strikes[strike] = {"ce_oi": ce_oi, "pe_oi": pe_oi}

        max_pain = None
        min_loss = float("inf")
        for candidate in strikes:
            loss = sum(
                max(0, candidate - s) * v["ce_oi"] +
                max(0, s - candidate) * v["pe_oi"]
                for s, v in strikes.items()
            )
            if loss < min_loss:
                min_loss = loss
                max_pain = candidate

        underlying = data["records"].get("underlyingValue", 0)
        return {
            "pcr": round(pcr, 4),
            "max_pain": max_pain,
            "underlying": underlying,
            "total_call_oi": total_call_oi,
            "total_put_oi": total_put_oi,
        }

    def reason(self, data: dict) -> AgentSignal:
        pcr = data.get("pcr", 1.0)
        underlying = data.get("underlying", 0)
        max_pain = data.get("max_pain", 0)
        pain_diff_pct = ((underlying - max_pain) / max_pain * 100
                         if max_pain else 0)

        if pcr > 1.3:
            signal, conf = 1, min(0.4 + (pcr - 1.3) * 0.5, 0.85)
            reason = (f"PCR={pcr:.2f} (bullish — high put OI protects "
                      f"downside). Max pain {max_pain}, "
                      f"underlying {pain_diff_pct:+.1f}% from pain.")
        elif pcr < 0.7:
            signal, conf = -1, min(0.4 + (0.7 - pcr) * 0.5, 0.85)
            reason = (f"PCR={pcr:.2f} (bearish — high call OI caps "
                      f"upside). Max pain {max_pain}.")
        else:
            signal, conf = 0, 0.3
            reason = (f"PCR={pcr:.2f} neutral range. "
                      f"Max pain {max_pain}.")
        return AgentSignal(
            agent_name=self.name, signal=signal,
            confidence=conf, reasoning=reason, raw_data=data
        )
