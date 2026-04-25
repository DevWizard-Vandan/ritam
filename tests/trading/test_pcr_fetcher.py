from datetime import datetime, timedelta, timezone

import requests

from src.trading.pcr_fetcher import clear_pcr_cache, fetch_nifty_pcr


IST = timezone(timedelta(hours=5, minutes=30))


class _Response:
    def __init__(self, payload=None, should_fail=False):
        self._payload = payload or {}
        self._should_fail = should_fail

    def raise_for_status(self):
        if self._should_fail:
            raise requests.HTTPError("boom")

    def json(self):
        return self._payload


def _session_factory_from_sequence(sequence, call_log):
    class _Session:
        def __init__(self):
            self._calls = 0

        def get(self, url, timeout=15, headers=None):
            call_log.append(url)
            response = sequence[self._calls]
            self._calls += 1
            if isinstance(response, Exception):
                raise response
            return response

        def close(self):
            pass

    return _Session


def test_fetch_nifty_pcr_computes_total_oi_and_pcr():
    clear_pcr_cache()
    calls = []
    payload = {
        "records": {
            "data": [
                {"CE": {"openInterest": 1000}, "PE": {"openInterest": 1500}},
                {"CE": {"openInterest": 500}, "PE": {"openInterest": 500}},
            ]
        }
    }
    session_factory = _session_factory_from_sequence(
        [_Response({}), _Response({}), _Response(payload)],
        calls,
    )

    snapshot = fetch_nifty_pcr(
        session_factory=session_factory,
        now_fn=lambda: datetime(2026, 4, 25, 10, 0, tzinfo=IST),
        force_refresh=True,
    )

    assert snapshot["available"] is True
    assert snapshot["ce_oi"] == 1500
    assert snapshot["pe_oi"] == 2000
    assert snapshot["pcr"] == 1.3333


def test_fetch_nifty_pcr_caches_second_call():
    clear_pcr_cache()
    calls = []
    payload = {"records": {"data": [{"CE": {"openInterest": 100}, "PE": {"openInterest": 100}}]}}
    session_factory = _session_factory_from_sequence(
        [_Response({}), _Response({}), _Response(payload)],
        calls,
    )
    now = datetime(2026, 4, 25, 10, 0, tzinfo=IST)

    first = fetch_nifty_pcr(session_factory=session_factory, now_fn=lambda: now, force_refresh=True)
    second = fetch_nifty_pcr(session_factory=session_factory, now_fn=lambda: now + timedelta(seconds=5))

    assert first["pcr"] == 1.0
    assert second["pcr"] == 1.0
    assert calls.count("https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY") == 1
    assert second["is_stale"] is False


def test_fetch_nifty_pcr_returns_neutral_fallback_on_empty_records():
    clear_pcr_cache()
    session_factory = _session_factory_from_sequence(
        [_Response({}), _Response({}), _Response({"records": {"data": []}})],
        [],
    )

    snapshot = fetch_nifty_pcr(
        session_factory=session_factory,
        now_fn=lambda: datetime(2026, 4, 25, 10, 0, tzinfo=IST),
        force_refresh=True,
    )

    assert snapshot["available"] is False
    assert snapshot["pcr"] == 1.0
    assert snapshot["status"] == "unavailable"


def test_fetch_nifty_pcr_retries_after_transient_failure():
    clear_pcr_cache()
    call_log = []
    attempts = {"count": 0}

    class _Session:
        def get(self, url, timeout=15, headers=None):
            call_log.append(url)
            if url == "https://www.nseindia.com":
                attempts["count"] += 1
            if attempts["count"] == 1 and url == "https://www.nseindia.com":
                raise requests.ConnectionError("transient")
            if url.endswith("option-chain-indices?symbol=NIFTY"):
                return _Response({"records": {"data": [{"CE": {"openInterest": 50}, "PE": {"openInterest": 75}}]}})
            return _Response({})

        def close(self):
            pass

    snapshot = fetch_nifty_pcr(
        session_factory=_Session,
        now_fn=lambda: datetime(2026, 4, 25, 10, 0, tzinfo=IST),
        max_retries=2,
        sleep_fn=lambda *_args: None,
        force_refresh=True,
    )

    assert snapshot["available"] is True
    assert snapshot["pcr"] == 1.5


def test_fetch_nifty_pcr_falls_back_when_all_retries_fail():
    clear_pcr_cache()

    class _Session:
        def get(self, url, timeout=15, headers=None):
            raise requests.Timeout("down")

        def close(self):
            pass

    snapshot = fetch_nifty_pcr(
        session_factory=_Session,
        now_fn=lambda: datetime(2026, 4, 25, 10, 0, tzinfo=IST),
        max_retries=2,
        sleep_fn=lambda *_args: None,
        force_refresh=True,
    )

    assert snapshot["available"] is False
    assert snapshot["pcr"] == 1.0
    assert snapshot["reason"].startswith("fetch_failed")


def test_fetch_nifty_pcr_marks_stale_cache_when_refresh_fails():
    clear_pcr_cache()
    payload = {"records": {"data": [{"CE": {"openInterest": 100}, "PE": {"openInterest": 200}}]}}

    class _FreshSession:
        def get(self, url, timeout=15, headers=None):
            if url.endswith("option-chain-indices?symbol=NIFTY"):
                return _Response(payload)
            return _Response({})

        def close(self):
            pass

    fresh = fetch_nifty_pcr(
        session_factory=_FreshSession,
        now_fn=lambda: datetime(2026, 4, 25, 10, 0, tzinfo=IST),
        force_refresh=True,
    )
    assert fresh["is_stale"] is False

    class _FailingSession:
        def get(self, url, timeout=15, headers=None):
            raise requests.Timeout("down")

        def close(self):
            pass

    stale = fetch_nifty_pcr(
        session_factory=_FailingSession,
        now_fn=lambda: datetime(2026, 4, 25, 10, 1, 5, tzinfo=IST),
        force_refresh=True,
    )

    assert stale["is_stale"] is True
    assert stale["status"] == "stale"
    assert stale["cache_age_seconds"] >= 65
