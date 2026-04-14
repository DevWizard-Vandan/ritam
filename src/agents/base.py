from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from typing import Any
import google.generativeai as genai
from loguru import logger

@dataclass
class AgentSignal:
    agent_name: str
    signal: int          # -1 bearish, 0 neutral, +1 bullish
    confidence: float    # 0.0 to 1.0
    reasoning: str
    raw_data: dict = field(default_factory=dict)

class AgentBase(ABC):
    """Base class for all Ritam intelligence agents."""
    name: str = "BaseAgent"
    assigned_api_key: str = ""
    fallback_api_key: str = ""   # Key 7 overflow

    def _gemini_call(self, prompt: str, model_name: str) -> str:
        """Makes Gemini call with assigned key, falls back to key 7."""
        from src.config import settings
        keys_to_try = [self.assigned_api_key, settings.GEMINI_API_KEY_7]
        for key in keys_to_try:
            if not key:
                continue
            try:
                genai.configure(api_key=key)
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                return response.text.strip()
            except Exception as e:
                logger.warning(f"{self.name} Gemini call failed "
                               f"(key ending ...{key[-4:]}): {e}")
        logger.error(f"{self.name}: all API keys exhausted")
        return ""

    @abstractmethod
    def collect(self) -> dict[str, Any]:
        """Fetch raw data. No Gemini calls here."""
        ...

    @abstractmethod
    def reason(self, data: dict[str, Any]) -> AgentSignal:
        """Produce a signal from collected data."""
        ...

    def run(self) -> AgentSignal:
        """Full agent execution: collect → reason → return signal."""
        try:
            data = self.collect()
            signal = self.reason(data)
            logger.info(f"{self.name}: signal={signal.signal} "
                        f"confidence={signal.confidence:.2f}")
            return signal
        except Exception as e:
            logger.error(f"{self.name} failed: {e}", exc_info=True)
            return AgentSignal(
                agent_name=self.name,
                signal=0, confidence=0.0,
                reasoning=f"Agent failed: {str(e)}"
            )