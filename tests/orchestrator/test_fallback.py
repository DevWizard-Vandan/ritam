import pytest
from src.agents.base import AgentSignal
from src.orchestrator.agent import _weighted_fallback


def _make_signal(name, signal, confidence):
    return AgentSignal(agent_name=name, signal=signal, confidence=confidence,
                       reasoning="test")


def test_balanced_signals_returns_neutral():
    """FII=-1/0.80, Breadth=+1/0.80, rest=0 → balanced → signal=0, conf~0.30"""
    signals = [
        _make_signal("FIIDerivativeAgent", -1, 0.80),
        _make_signal("MarketBreadthAgent", 1, 0.80),
        _make_signal("TechnicalPatternAgent", 0, 0.50),
        _make_signal("RegimeCrossCheckAgent", 0, 0.50),
        _make_signal("NewsImpactAgent", 0, 0.50),
        _make_signal("OptionsChainAgent", 0, 0.50),
        _make_signal("SectorRotationAgent", 0, 0.50),
        _make_signal("GlobalMarketAgent", 0, 0.50),
    ]
    result = _weighted_fallback(signals, "trending_up")
    assert result.signal == 0
    assert abs(result.confidence - 0.30) < 0.05


def test_bearish_majority_returns_sell():
    """FII=-1/0.80, Breadth=-1/0.50, Tech=-1/0.60 → signal=-1"""
    signals = [
        _make_signal("FIIDerivativeAgent", -1, 0.80),
        _make_signal("MarketBreadthAgent", -1, 0.50),
        _make_signal("TechnicalPatternAgent", -1, 0.60),
        _make_signal("RegimeCrossCheckAgent", 0, 0.30),
        _make_signal("NewsImpactAgent", 0, 0.30),
    ]
    result = _weighted_fallback(signals, "trending_down")
    assert result.signal == -1
    assert result.confidence > 0.10


def test_crisis_regime_always_bearish():
    """Crisis regime always → signal=-1 with conf=0.70"""
    signals = [
        _make_signal("FIIDerivativeAgent", 1, 0.90),
        _make_signal("MarketBreadthAgent", 1, 0.90),
    ]
    result = _weighted_fallback(signals, "crisis")
    assert result.signal == -1
    assert result.confidence == 0.70


def test_economic_calendar_uncertainty_penalty():
    """EconomicCalendarAgent conf=0.60 → final_conf reduced by 0.12"""
    signals = [
        _make_signal("FIIDerivativeAgent", -1, 0.80),
        _make_signal("MarketBreadthAgent", -1, 0.80),
        _make_signal("TechnicalPatternAgent", -1, 0.80),
        _make_signal("EconomicCalendarAgent", 0, 0.60),
    ]
    # Without penalty: bearish raw_score, base conf computed from raw_score * 0.8
    result_no_eco = _weighted_fallback(signals[:3], "trending_down")
    result_with_eco = _weighted_fallback(signals, "trending_down")
    # Penalty = 0.60 * 0.20 = 0.12
    assert abs(result_no_eco.confidence - result_with_eco.confidence - 0.12) < 0.005


def test_agent_name_from_fallback():
    """Result agent_name should be WeightedFallback"""
    signals = [_make_signal("FIIDerivativeAgent", 1, 0.80)]
    result = _weighted_fallback(signals, "trending_up")
    assert result.agent_name == "WeightedFallback"


def test_unknown_agent_uses_default_weight():
    """Unknown agent name gets default weight 0.01 — does not crash"""
    signals = [_make_signal("UnknownAgent", 1, 0.90)]
    result = _weighted_fallback(signals, "choppy")
    assert result is not None


def test_empty_signals_returns_neutral():
    """Empty signal list → neutral, conf floored at 0.10"""
    result = _weighted_fallback([], "choppy")
    assert result.signal == 0
    assert result.confidence >= 0.10
