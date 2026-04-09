"""News ingestion pipeline for Indian market headlines."""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any

try:
    import requests
except ModuleNotFoundError:  # pragma: no cover - environment fallback
    class _RequestsFallback:
        @staticmethod
        def get(*_args, **_kwargs):
            raise RuntimeError("requests is not installed")

    requests = _RequestsFallback()

try:
    import feedparser
except ModuleNotFoundError:  # pragma: no cover - environment fallback
    feedparser = None

try:
    from apscheduler.schedulers.background import BackgroundScheduler
except ModuleNotFoundError:  # pragma: no cover - environment fallback
    BackgroundScheduler = None
try:
    from loguru import logger
except ModuleNotFoundError:  # pragma: no cover - environment fallback
    import logging
    logger = logging.getLogger(__name__)

from src.config.settings import settings
from src.data.db import init_db, write_news_raw
from src.sentiment.preprocessor import clean_headlines

IST = ZoneInfo(settings.TIMEZONE)

NEWS_API_URL = "https://newsapi.org/v2/top-headlines"
RSS_FEEDS: tuple[tuple[str, str], ...] = (
    ("moneycontrol", "https://www.moneycontrol.com/rss/business.xml"),
    ("et_markets", "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms"),
)


def _fetch_newsapi_headlines(timeout: int = 10) -> list[dict[str, str]]:
    """Fetch raw headline records from NewsAPI."""
    if not settings.NEWS_API_KEY:
        logger.warning("NEWS_API_KEY missing; skipping NewsAPI call")
        return []

    params = {
        "apiKey": settings.NEWS_API_KEY,
        "country": "in",
        "category": "business",
        "pageSize": 50,
    }

    try:
        response = requests.get(NEWS_API_URL, params=params, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:  # noqa: BLE001 - log and continue with RSS fallback
        logger.warning(f"NewsAPI fetch failed: {exc}")
        return []

    articles = payload.get("articles") or []
    headlines: list[dict[str, str]] = []
    for article in articles:
        title = (article.get("title") or "").strip()
        if not title:
            continue
        headlines.append(
            {
                "source": (article.get("source") or {}).get("name") or "newsapi",
                "headline": title,
                "url": article.get("url") or "",
                "published_at": article.get("publishedAt") or "",
            }
        )

    return headlines


def _fetch_rss_headlines() -> list[dict[str, str]]:
    """Fetch raw headline records from backup RSS feeds."""
    headlines: list[dict[str, str]] = []

    if feedparser is None:
        logger.warning("feedparser is not installed; RSS fallback unavailable")
        return headlines

    for source, url in RSS_FEEDS:
        parsed = feedparser.parse(url)
        for entry in parsed.entries:
            title = (getattr(entry, "title", "") or "").strip()
            if not title:
                continue
            headlines.append(
                {
                    "source": source,
                    "headline": title,
                    "url": getattr(entry, "link", "") or "",
                    "published_at": getattr(entry, "published", "") or "",
                }
            )

    return headlines


def _dedupe_records(records: list[dict[str, str]]) -> list[dict[str, str]]:
    """Deduplicate by URL when present, else by source+headline."""
    unique: list[dict[str, str]] = []
    seen_keys: set[str] = set()

    for record in records:
        key = record["url"] or f"{record['source']}::{record['headline'].lower()}"
        if key in seen_keys:
            continue
        seen_keys.add(key)
        unique.append(record)

    return unique


def fetch_headlines() -> list[str]:
    """Fetch latest Indian market headlines, persist raw records, and return cleaned headline strings."""
    init_db()

    records = _fetch_newsapi_headlines()
    if not records:
        records = _fetch_rss_headlines()

    records = _dedupe_records(records)
    fetched_at = datetime.now(IST).isoformat()

    if records:
        write_news_raw(
            [
                {
                    "source": rec["source"],
                    "headline": rec["headline"],
                    "url": rec["url"],
                    "published_at": rec["published_at"],
                    "fetched_at": fetched_at,
                }
                for rec in records
            ]
        )

    cleaned = clean_headlines([rec["headline"] for rec in records])
    logger.info(f"Fetched {len(cleaned)} clean headlines")
    return cleaned


def build_news_scheduler() -> BackgroundScheduler:
    """Create and start a scheduler that fetches headlines every 5 minutes."""
    if BackgroundScheduler is None:
        raise RuntimeError("apscheduler is not installed")

    scheduler = BackgroundScheduler(timezone=settings.TIMEZONE)
    scheduler.add_job(fetch_headlines, trigger="interval", minutes=5, id="news_fetch_job", replace_existing=True)
    scheduler.start()
    return scheduler
