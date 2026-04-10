from unittest.mock import patch

from src.reasoning.regime_classifier import classify_regime, VALID_REGIMES, REGIME_PROMPT


@patch('src.reasoning.regime_classifier.quick_reason')
def test_classify_regime_real_market_description(mock_quick_reason):
    """Test that classify_regime() called with a numeric market indicators returns one of VALID_REGIMES. Mock quick_reason to return each VALID_REGIME value in turn."""
    for regime in VALID_REGIMES:
        mock_quick_reason.return_value = regime
        result = classify_regime(
            price_change_pct=1.23,
            vix=14.5,
            news_count=42,
            sentiment=0.75
        )
        assert result in VALID_REGIMES
        assert result == regime

@patch('src.reasoning.regime_classifier.quick_reason')
def test_market_summary_prompt_formatting(mock_quick_reason):
    """Test that a 2-sentence market summary prompt formats correctly in REGIME_PROMPT."""
    mock_quick_reason.return_value = "baseline"

    classify_regime(
        price_change_pct=-2.555,
        vix=22.14,
        news_count=105,
        sentiment=-0.804
    )

    expected_prompt = REGIME_PROMPT.format(
        price_change_pct=-2.56,
        vix=22.1,
        news_count=105,
        sentiment=-0.80
    )

    mock_quick_reason.assert_called_once_with(expected_prompt)
