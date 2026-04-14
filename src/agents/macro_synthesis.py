from src.agents.base import AgentBase, AgentSignal
from loguru import logger

class MacroSynthesisAgent(AgentBase):
    """Meta-agent: synthesizes all other agent signals into one verdict."""
    name = "MacroSynthesisAgent"
    # assigned_api_key set from settings.GEMINI_API_KEY_4 at runtime

    def collect(self) -> dict:
        # Synthesis agent receives signals as input — collect is a no-op
        return {}

    def reason(self, data: dict) -> AgentSignal:
        """
        data must contain:
          - agent_signals: list of AgentSignal (from all other agents)
          - regime: str (from primary regime classifier)
          - analog_summary: str (from analog finder)
        """
        from src.config import settings
        agent_signals = data.get("agent_signals", [])
        regime = data.get("regime", "unknown")
        analog_summary = data.get("analog_summary", "")

        if not agent_signals:
            return AgentSignal(
                agent_name=self.name, signal=0, confidence=0.0,
                reasoning="No agent signals provided", raw_data=data
            )

        signals_text = "\n".join(
            f"- {s.agent_name}: signal={s.signal:+d}, "
            f"conf={s.confidence:.2f}, reason={s.reasoning[:100]}"
            for s in agent_signals
        )
        model = (settings.GEMINI_PRO_MODEL if settings.GEMINI_USE_PRO
                 else settings.GEMINI_FLASH_LITE_MODEL)
        prompt = f"""You are a quantitative market analyst synthesizing multiple signals
for a Nifty 50 intraday prediction.

Current regime: {regime}
Historical analog summary: {analog_summary}

Agent signals (signal: +1=bullish, -1=bearish, 0=neutral, conf=0-1):
{signals_text}

Rules:
- Weight high-confidence signals more
- If regime=crisis: override to -1 unless 4+ signals are strongly bullish
- If EconomicCalendarAgent signals uncertainty: reduce final confidence by 20%
- Require 2+ bullish signals with conf>0.5 to output +1
- Require 2+ bearish signals with conf>0.5 to output -1

Respond ONLY with valid JSON, no markdown:
{{"signal": 1|-1|0,
  "confidence": 0.0-1.0,
  "dominant_theme": "brief description of why",
  "dissenting_agents": ["list of agent names that disagreed"],
  "reasoning": "2-3 sentences explaining the synthesis"}}"""

        raw = self._gemini_call(prompt, model)
        try:
            import json, re
            clean = re.sub(r"```(?:json)?|```", "", raw).strip()
            parsed = json.loads(clean)
            return AgentSignal(
                agent_name=self.name,
                signal=int(parsed.get("signal", 0)),
                confidence=float(parsed.get("confidence", 0.3)),
                reasoning=parsed.get("reasoning", ""),
                raw_data={**data, "parsed": parsed}
            )
        except Exception as e:
            logger.warning(f"MacroSynthesisAgent parse failed: {e}")
            return AgentSignal(
                agent_name=self.name, signal=0,
                confidence=0.1, reasoning=raw[:300], raw_data=data
            )
