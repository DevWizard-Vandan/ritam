"""Unit tests for scorer.py — mocks HuggingFace pipeline."""
import pytest
from unittest.mock import patch, MagicMock


MOCK_OUTPUT = [[
    {"label": "positive", "score": 0.92},
    {"label": "negative", "score": 0.05},
    {"label": "neutral",  "score": 0.03}
]]


def test_score_empty_list_returns_empty():
    from src.sentiment.scorer import score_headlines
    assert score_headlines([]) == []


def test_score_returns_correct_keys():
    with patch("src.sentiment.scorer._load_pipeline") as mock_pipe:
        mock_pipe.return_value = MagicMock(return_value=MOCK_OUTPUT)
        from src.sentiment.scorer import score_headlines
        results = score_headlines(["Nifty hits record high"])
        assert "headline" in results[0]
        assert "label" in results[0]
        assert "score" in results[0]
        assert "confidence" in results[0]


def test_positive_headline_has_positive_score():
    with patch("src.sentiment.scorer._load_pipeline") as mock_pipe:
        mock_pipe.return_value = MagicMock(return_value=MOCK_OUTPUT)
        from src.sentiment.scorer import score_headlines
        results = score_headlines(["Nifty hits record high"])
        assert results[0]["score"] > 0


def test_score_confidence_between_0_and_1():
    with patch("src.sentiment.scorer._load_pipeline") as mock_pipe:
        mock_pipe.return_value = MagicMock(return_value=MOCK_OUTPUT)
        from src.sentiment.scorer import score_headlines
        results = score_headlines(["Market crash"])
        assert 0 <= results[0]["confidence"] <= 1
