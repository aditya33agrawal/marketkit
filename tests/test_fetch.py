import pandas as pd
import pytest

from marketkit import clean, fetch
from marketkit.errors import DataUnavailable, InvalidRequest, RateLimited, SourceError


def _raw_frame(start="2024-01-01", end=None, periods=None):
    if periods is not None:
        idx = pd.date_range(start, periods=periods)
    else:
        idx = pd.date_range(start, end)
    n = len(idx)
    return pd.DataFrame(
        {
            "Open": range(n),
            "High": range(n),
            "Low": range(n),
            "Close": range(n),
            "Volume": [100] * n,
        },
        index=idx,
    )


def _canonical_frame(start="2024-01-01", periods=5):
    return clean.normalize(_raw_frame(start=start, periods=periods), source="yahoo")


class FakeSource:
    def __init__(self, name, *, fail_with=None):
        self.name = name
        self.requires_key = False
        self.fail_with = fail_with
        self.calls = 0

    def fetch(self, ticker, start, end, interval):
        self.calls += 1
        if self.fail_with is not None:
            raise self.fail_with(f"{self.name} failed")
        return _raw_frame(start=start, end=end)


class ExplodingSource:
    """A source that fails the test if it's ever called."""

    def __init__(self, name):
        self.name = name
        self.requires_key = False

    def fetch(self, *a, **kw):
        raise AssertionError(f"{self.name} should not have been called")


def test_fallback_to_second_source_on_rate_limit(monkeypatch):
    yahoo = FakeSource("yahoo", fail_with=RateLimited)
    stooq = FakeSource("stooq")
    registry = {"yahoo": yahoo, "stooq": stooq}
    monkeypatch.setattr(fetch, "get_source", lambda name: registry[name])

    df = fetch.get("AAPL", sources=["yahoo", "stooq"], period="1y")

    assert yahoo.calls == 1
    assert stooq.calls == 1
    assert not df.empty


def test_all_sources_fail_raises_data_unavailable(monkeypatch):
    yahoo = FakeSource("yahoo", fail_with=SourceError)
    stooq = FakeSource("stooq", fail_with=SourceError)
    registry = {"yahoo": yahoo, "stooq": stooq}
    monkeypatch.setattr(fetch, "get_source", lambda name: registry[name])

    with pytest.raises(DataUnavailable):
        fetch.get("AAPL", sources=["yahoo", "stooq"], period="1y")


def test_fresh_cache_skips_all_sources(monkeypatch):
    yahoo = ExplodingSource("yahoo")
    registry = {"yahoo": yahoo}
    monkeypatch.setattr(fetch, "get_source", lambda name: registry[name])

    # prime the cache via a working fake fetch path first
    working = FakeSource("yahoo")
    monkeypatch.setattr(fetch, "get_source", lambda name: working)
    fetch.get("AAPL", sources=["yahoo"], period="1y")

    # now swap in the exploding source; cached data should be used instead
    monkeypatch.setattr(fetch, "get_source", lambda name: registry[name])
    df = fetch.get("AAPL", sources=["yahoo"], period="1y")
    assert not df.empty


def test_offline_with_no_cache_raises(monkeypatch):
    monkeypatch.setattr(fetch, "get_source", lambda name: ExplodingSource(name))
    with pytest.raises(DataUnavailable):
        fetch.get("AAPL", sources=["yahoo"], period="1y", offline=True)


def test_invalid_date_range_raises_invalid_request():
    with pytest.raises(InvalidRequest):
        fetch.get("AAPL", start="2024-06-01", end="2024-01-01")


def test_multi_ticker_skips_failures(monkeypatch):
    def get_source(name):
        return FakeSource(name)

    monkeypatch.setattr(fetch, "get_source", get_source)

    def fake_get_one(ticker, start, end, interval, sources, offline):
        if ticker == "BAD":
            raise DataUnavailable("bad ticker")
        return _canonical_frame()

    monkeypatch.setattr(fetch, "_get_one", fake_get_one)
    out = fetch.get(["AAPL", "BAD"], period="1y")
    assert set(out["ticker"].unique()) == {"AAPL"}
