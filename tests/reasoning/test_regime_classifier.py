import pytest
from unittest.mock import patch
from src.reasoning.regime_classifier import classify_regime, REGIME_PROMPT, VALID_REGIMES

@pytest.mark.parametrize("regime", VALID_REGIMES)
@patch('src.reasoning.regime_classifier.quick_reason')
def test_classify_regime_valid_output(mock_quick_reason, regime):
    """Test that every valid regime response is parsed and returned correctly."""
    mock_quick_reason.return_value = regime

    result = classify_regime(1.5, 12.0, 50, 0.8)

    assert result == regime
    mock_quick_reason.assert_called_once()

@patch('src.reasoning.regime_classifier.quick_reason')
def test_classify_regime_case_insensitive(mock_quick_reason):
    """Test that the response is lowercased correctly."""
    mock_quick_reason.return_value = " CRISIS "

    result = classify_regime(-5.0, 30.0, 100, -0.9)

    assert result == "crisis"

@patch('src.reasoning.regime_classifier.quick_reason')
def test_classify_regime_strips_punctuation(mock_quick_reason):
    """Test that trailing periods are stripped."""
    mock_quick_reason.return_value = "recovery."

    result = classify_regime(2.0, 15.0, 40, 0.5)

    assert result == "recovery"

@patch('src.reasoning.regime_classifier.quick_reason')
def test_classify_regime_invalid_fallback(mock_quick_reason):
    """Test that an unrecognized response falls back to 'baseline'."""
    mock_quick_reason.return_value = "unknown_market_state"

    result = classify_regime(0.5, 14.0, 30, 0.1)

    assert result == "baseline"

@patch('src.reasoning.regime_classifier.quick_reason')
def test_classify_regime_prompt_formatting(mock_quick_reason):
    """Test that the prompt is formatted with the correct rounded values."""
    mock_quick_reason.return_value = "choppy"

    # Pass unrounded values to see if they are formatted correctly
    classify_regime(1.234, 15.678, 25, 0.456)

    expected_prompt = REGIME_PROMPT.format(
        price_change_pct=1.23,
        vix=15.7,
        news_count=25,
        sentiment=0.46
    )

    mock_quick_reason.assert_called_once_with(expected_prompt)
