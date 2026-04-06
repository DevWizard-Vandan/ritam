# Task 003 — News Ingestion Pipeline
**Assigned to:** Codex
**Status:** TODO
**Phase:** 1 — Data Pipeline
**Depends on:** Task 002 (db.py must exist for saving headlines)

## Goal
Build src/data/news_feed.py that:
- Fetches top financial headlines from NewsAPI (categories: business, finance, India markets)
- Also scrapes MoneyControl and ET Markets RSS feeds as backup sources
- Saves each headline to SQLite: (id, source, headline, url, published_at_ist, fetched_at)
- Runs every 15 minutes via APScheduler
- Deduplicates headlines (do not re-save same URL)

## Inputs
- NEWS_API_KEY from .env
- db.py for database writes

## Outputs
- src/data/news_feed.py
- tests/data/test_news_feed.py

## Definition of Done
- [ ] NewsAPI fetch works and saves to DB
- [ ] RSS feed parsing works
- [ ] Deduplication logic tested
- [ ] 5+ unit tests passing
- [ ] STATUS.md updated

