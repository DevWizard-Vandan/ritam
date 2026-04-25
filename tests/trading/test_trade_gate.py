from datetime import datetime, timedelta, timezone

from src.trading.trade_gate import evaluate_trade


IST = timezone(timedelta(hours=5, minutes=30))


def _pcr(pcr_value=1.0, available=True):
    return {
        "available": available,
        "status": "ok" if available else "unavailable",
        "reason": "ok" if available else "fetch_failed",
        "ce_oi": 1000,
        "pe_oi": 1000,
        "pcr": pcr_value,
        "fetched_at": datetime(2026, 4, 25, 10, 0, tzinfo=IST).isoformat(),
    }


def test_trade_gate_blocks_non_trending_regime():
    result = evaluate_trade(
        regime="ranging",
        analog_bias="bullish",
        confidence=0.9,
        timestamp=datetime(2026, 4, 25, 10, 0, tzinfo=IST),
        pcr_fetcher=lambda: _pcr(),
    )

    assert result["decision"] == "NO_TRADE"
    assert result["reason_code"] == "REGIME_BLOCK"


def test_trade_gate_blocks_implicit_trending_alias():
    result = evaluate_trade(
        regime="trending",
        analog_bias="bullish",
        confidence=0.9,
        timestamp=datetime(2026, 4, 25, 10, 0, tzinfo=IST),
        pcr_fetcher=lambda: _pcr(),
    )

    assert result["decision"] == "NO_TRADE"
    assert result["reason_code"] == "REGIME_BLOCK"


def test_trade_gate_blocks_low_confidence():
    result = evaluate_trade(
        regime="trending_up",
        analog_bias="bullish",
        confidence=0.64,
        timestamp=datetime(2026, 4, 25, 10, 0, tzinfo=IST),
        pcr_fetcher=lambda: _pcr(),
    )

    assert result["decision"] == "NO_TRADE"
    assert result["reason_code"] == "LOW_EFFECTIVE_CONFIDENCE"


def test_trade_gate_blocks_restricted_opening_window():
    result = evaluate_trade(
        regime="trending_up",
        analog_bias="bullish",
        confidence=0.8,
        timestamp=datetime(2026, 4, 25, 9, 20, tzinfo=IST),
        pcr_fetcher=lambda: _pcr(),
    )

    assert result["decision"] == "NO_TRADE"
    assert result["reason_code"] == "TIME_BLOCK"


def test_trade_gate_allows_neutral_pcr_band():
    result = evaluate_trade(
        regime="trending",
        analog_bias="bullish",
        confidence=0.7,
        timestamp=datetime(2026, 4, 25, 10, 15, tzinfo=IST),
        pcr_fetcher=lambda: _pcr(1.05),
    )

    assert result["decision"] == "NO_TRADE"
    assert result["signal"] is None
    assert result["reason_code"] == "REGIME_BLOCK"


def test_trade_gate_allows_neutral_pcr_band_with_explicit_regime():
    result = evaluate_trade(
        regime="trending_up",
        analog_bias="bullish",
        confidence=0.7,
        timestamp=datetime(2026, 4, 25, 10, 15, tzinfo=IST),
        pcr_fetcher=lambda: _pcr(1.05),
    )

    assert result["decision"] == "TRADE"
    assert result["signal"] == "BUY_CALL"
    assert result["reason_code"] == "TRADE_ALLOWED"


def test_trade_gate_applies_mild_pcr_penalty_deterministically():
    result = evaluate_trade(
        regime="trending_up",
        analog_bias="bearish",
        confidence=0.80,
        timestamp=datetime(2026, 4, 25, 10, 15, tzinfo=IST),
        pcr_fetcher=lambda: _pcr(1.42),
    )

    assert result["decision"] == "TRADE"
    assert result["signal"] == "BUY_PUT"
    assert result["details"]["confidence_original"] == 0.8
    assert result["details"]["confidence_penalty"] == -0.1
    assert result["details"]["confidence_adjusted"] == 0.7


def test_trade_gate_blocks_extreme_pcr():
    result = evaluate_trade(
        regime="trending_up",
        analog_bias="bullish",
        confidence=0.9,
        timestamp=datetime(2026, 4, 25, 10, 15, tzinfo=IST),
        pcr_fetcher=lambda: _pcr(1.7),
    )

    assert result["decision"] == "NO_TRADE"
    assert result["reason_code"] == "PCR_EXTREME"


def test_trade_gate_treats_unavailable_pcr_as_neutral():
    pcr_snapshot = _pcr(1.0, available=False)
    pcr_snapshot["fetched_at"] = datetime(2026, 4, 25, 10, 15, tzinfo=IST).isoformat()
    result = evaluate_trade(
        regime="trending_up",
        analog_bias="bullish",
        confidence=0.7,
        timestamp=datetime(2026, 4, 25, 10, 15, tzinfo=IST),
        pcr_fetcher=lambda: pcr_snapshot,
    )

    assert result["decision"] == "TRADE"
    assert result["reason_code"] == "TRADE_ALLOWED"
    assert result["details"]["pcr_is_stale"] is False


def test_trade_gate_marks_stale_pcr_details():
    stale_snapshot = _pcr(1.05)
    stale_snapshot.update({
        "status": "stale",
        "is_stale": True,
        "cache_age_seconds": 61.2,
    })
    result = evaluate_trade(
        regime="trending_up",
        analog_bias="bullish",
        confidence=0.7,
        timestamp=datetime(2026, 4, 25, 10, 15, tzinfo=IST),
        pcr_fetcher=lambda: stale_snapshot,
    )

    assert result["details"]["pcr_is_stale"] is True
    assert result["details"]["pcr_cache_age_seconds"] == 61.2
