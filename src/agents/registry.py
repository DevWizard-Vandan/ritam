"""Agent registry — add new agents here, orchestrator picks them up."""
from src.agents.base import AgentBase
from src.agents.options_chain import OptionsChainAgent
from src.agents.market_breadth import MarketBreadthAgent
from src.agents.global_market import GlobalMarketAgent
from src.agents.sector_rotation import SectorRotationAgent
from src.agents.fii_derivative import FIIDerivativeAgent
from src.agents.economic_calendar import EconomicCalendarAgent
from src.agents.technical_pattern import TechnicalPatternAgent
from src.agents.news_impact import NewsImpactAgent
from src.agents.regime_crosscheck import RegimeCrossCheckAgent
from src.agents.macro_synthesis import MacroSynthesisAgent

REGISTERED_AGENTS: list[type[AgentBase]] = [
    OptionsChainAgent, MarketBreadthAgent, GlobalMarketAgent,
    SectorRotationAgent, FIIDerivativeAgent, EconomicCalendarAgent,
    TechnicalPatternAgent, NewsImpactAgent, RegimeCrossCheckAgent,
    MacroSynthesisAgent,
]
