"""Unit tests for src.data.news_fetcher."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src.data import news_fetcher


class DummyResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_fetch_headlines_uses_newsapi_and_stores_raw(monkeypatch):
    payload = {
        "articles": [
            {
                "source": {"name": "News Source"},
                "title": "  RBI policy keeps rates unchanged  ",
                "url": "https://example.com/rbi",
                "publishedAt": "2026-04-09T06:00:00Z",
            }
        ]
    }

    monkeypatch.setattr(news_fetcher.settings, "NEWS_API_KEY", "test-key")
    monkeypatch.setattr(news_fetcher.requests, "get", lambda *args, **kwargs: DummyResponse(payload))

    mock_write = Mock()
    monkeypatch.setattr(news_fetcher, "write_news_raw", mock_write)
    monkeypatch.setattr(news_fetcher, "init_db", Mock())

    cleaned = news_fetcher.fetch_headlines()

    assert cleaned == ["RBI policy keeps rates unchanged"]
    assert mock_write.call_count == 1
    stored_records = mock_write.call_args.args[0]
    assert stored_records[0]["source"] == "News Source"
    assert stored_records[0]["url"] == "https://example.com/rbi"


def test_fetch_headlines_falls_back_to_rss_when_newsapi_fails(monkeypatch):
    monkeypatch.setattr(news_fetcher.settings, "NEWS_API_KEY", "test-key")
    monkeypatch.setattr(news_fetcher.requests, "get", Mock(side_effect=RuntimeError("boom")))

    rss_entry = SimpleNamespace(title="Sensex rises 500 points", link="https://mc.com/1", published="now")
    monkeypatch.setattr(news_fetcher, "feedparser", SimpleNamespace(parse=lambda _url: SimpleNamespace(entries=[rss_entry])))

    mock_write = Mock()
    monkeypatch.setattr(news_fetcher, "write_news_raw", mock_write)
    monkeypatch.setattr(news_fetcher, "init_db", Mock())

    cleaned = news_fetcher.fetch_headlines()

    assert cleaned == ["Sensex rises 500 points"]
    assert mock_write.call_count == 1


def test_fetch_headlines_deduplicates_records(monkeypatch):
    payload = {
        "articles": [
            {"source": {"name": "A"}, "title": "One", "url": "https://dup", "publishedAt": ""},
            {"source": {"name": "B"}, "title": "One again", "url": "https://dup", "publishedAt": ""},
        ]
    }

    monkeypatch.setattr(news_fetcher.settings, "NEWS_API_KEY", "test-key")
    monkeypatch.setattr(news_fetcher.requests, "get", lambda *args, **kwargs: DummyResponse(payload))

    mock_write = Mock()
    monkeypatch.setattr(news_fetcher, "write_news_raw", mock_write)
    monkeypatch.setattr(news_fetcher, "init_db", Mock())

    cleaned = news_fetcher.fetch_headlines()

    assert cleaned == ["One"]
    assert len(mock_write.call_args.args[0]) == 1


def test_fetch_headlines_uses_rss_when_api_key_missing(monkeypatch):
    monkeypatch.setattr(news_fetcher.settings, "NEWS_API_KEY", "")

    rss_entry = SimpleNamespace(title=" Nifty closes higher ", link="https://et.com/2", published="today")
    monkeypatch.setattr(news_fetcher, "feedparser", SimpleNamespace(parse=lambda _url: SimpleNamespace(entries=[rss_entry])))

    monkeypatch.setattr(news_fetcher, "write_news_raw", Mock())
    monkeypatch.setattr(news_fetcher, "init_db", Mock())

    cleaned = news_fetcher.fetch_headlines()

    assert cleaned == ["Nifty closes higher"]


def test_build_news_scheduler_registers_five_minute_job(monkeypatch):
    class DummyScheduler:
        def __init__(self, timezone=None):
            self.timezone = timezone
            self.calls = []
            self.started = False

        def add_job(self, *args, **kwargs):
            self.calls.append((args, kwargs))

        def start(self):
            self.started = True

    dummy = DummyScheduler()
    monkeypatch.setattr(news_fetcher, "BackgroundScheduler", lambda timezone=None: dummy)

    scheduler = news_fetcher.build_news_scheduler()

    assert scheduler is dummy
    assert dummy.started is True
    assert len(dummy.calls) == 1
    args, kwargs = dummy.calls[0]
    assert args[0] == news_fetcher.fetch_headlines
    assert kwargs["trigger"] == "interval"
    assert kwargs["minutes"] == 5
