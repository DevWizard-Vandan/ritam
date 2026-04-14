from src.agents.base import AgentBase
from src.agents.macro_synthesis import MacroSynthesisAgent

def build_agents() -> list[AgentBase]:
    """Instantiates all agents with their assigned API keys."""
    from src.config import settings
    from src.agents.options_chain import OptionsChainAgent
    from src.agents.market_breadth import MarketBreadthAgent
    from src.agents.global_market import GlobalMarketAgent
    from src.agents.sector_rotation import SectorRotationAgent
    from src.agents.fii_derivative import FIIDerivativeAgent
    from src.agents.economic_calendar import EconomicCalendarAgent
    from src.agents.technical_pattern import TechnicalPatternAgent
    from src.agents.news_impact import NewsImpactAgent
    from src.agents.regime_crosscheck import RegimeCrossCheckAgent

    agents = [
        OptionsChainAgent(),
        MarketBreadthAgent(),
        GlobalMarketAgent(),
        SectorRotationAgent(),
        FIIDerivativeAgent(),
        EconomicCalendarAgent(),
    ]
    # Gemini-powered agents get their dedicated keys
    tech = TechnicalPatternAgent()
    tech.assigned_api_key = settings.GEMINI_API_KEY_3
    agents.append(tech)

    news = NewsImpactAgent()
    news.assigned_api_key = settings.GEMINI_API_KEY_5
    news.timeout_seconds = 25
    agents.append(news)

    regime_xc = RegimeCrossCheckAgent()
    regime_xc.assigned_api_key = settings.GEMINI_API_KEY_6
    agents.append(regime_xc)

    return agents

def build_synthesis_agent() -> MacroSynthesisAgent:
    from src.config import settings
    from src.agents.macro_synthesis import MacroSynthesisAgent
    synth = MacroSynthesisAgent()
    synth.assigned_api_key = settings.GEMINI_API_KEY_4
    return synth
