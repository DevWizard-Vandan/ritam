"""Tests for regime_classifier.py."""
import pytest
from unittest.mock import patch


def test_classify_regime_returns_valid_value():
    with patch("src.reasoning.regime_classifier.quick_reason", return_value="trending_up"):
        from src.reasoning.regime_classifier import classify_regime
        result = classify_regime(1.5, 14.0, 20, 0.65)
        assert result == "trending_up"


def test_classify_regime_defaults_on_invalid_response():
    with patch("src.reasoning.regime_classifier.quick_reason", return_value="something_random"):
        from src.reasoning.regime_classifier import classify_regime
        result = classify_regime(-3.0, 28.0, 100, -0.8)
        assert result == "baseline"


def test_all_valid_regimes_accepted():
    valid = ["crisis", "recovery", "trending_up", "trending_down", "choppy", "baseline"]
    for regime in valid:
        with patch("src.reasoning.regime_classifier.quick_reason", return_value=regime):
            from importlib import reload
            import src.reasoning.regime_classifier as rc
            reload(rc)
            result = rc.classify_regime(0, 18.0, 10, 0.0)
            assert result == regime
