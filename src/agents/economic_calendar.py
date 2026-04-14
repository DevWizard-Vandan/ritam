from src.agents.base import AgentBase, AgentSignal
from loguru import logger

class EconomicCalendarAgent(AgentBase):
    name = "EconomicCalendarAgent"
    # Pure local logic — no API, no Gemini

    # Key events for FY2026 — update annually
    EVENTS = [
        {"name": "RBI MPC", "dates": [
            "2026-04-09", "2026-06-04", "2026-08-06",
            "2026-10-01", "2026-12-03", "2027-02-05"
        ]},
        {"name": "US Fed FOMC", "dates": [
            "2026-04-29", "2026-06-11", "2026-07-30",
            "2026-09-17", "2026-11-05", "2026-12-17"
        ]},
        {"name": "India CPI", "dates": [
            "2026-04-14", "2026-05-13", "2026-06-12",
            "2026-07-14", "2026-08-13", "2026-09-14"
        ]},
        {"name": "India GDP", "dates": [
            "2026-05-29", "2026-08-28", "2026-11-27"
        ]},
    ]

    def collect(self) -> dict:
        from datetime import date, datetime
        today = date.today()
        upcoming = []
        for event in self.EVENTS:
            for ds in event["dates"]:
                d = datetime.strptime(ds, "%Y-%m-%d").date()
                delta = (d - today).days
                if 0 <= delta <= 7:
                    upcoming.append({
                        "name": event["name"],
                        "date": ds,
                        "days_away": delta
                    })
        upcoming.sort(key=lambda x: x["days_away"])
        return {"upcoming_events": upcoming, "today": str(today)}

    def reason(self, data: dict) -> AgentSignal:
        events = data.get("upcoming_events", [])
        if not events:
            return AgentSignal(
                agent_name=self.name, signal=0, confidence=0.15,
                reasoning="No major macro events in next 7 days",
                raw_data=data
            )
        nearest = events[0]
        days = nearest["days_away"]
        name = nearest["name"]

        # Event proximity = uncertainty = reduce confidence of other signals
        # Signal 0 = "be cautious", confidence reflects proximity risk
        conf = max(0.15, 0.60 - days * 0.08)
        reason = (f"⚠ {name} in {days} day(s) — "
                  f"macro uncertainty elevated. "
                  f"All upcoming: {[e['name'] for e in events]}")
        return AgentSignal(
            agent_name=self.name, signal=0,
            confidence=conf, reasoning=reason, raw_data=data
        )
