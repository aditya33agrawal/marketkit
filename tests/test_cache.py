import pandas as pd

from marketkit import cache, clean

INDEX = pd.date_range("2024-01-01", periods=3, name="date")
DF = pd.DataFrame(
    {
        "open": [1.0, 2.0, 3.0],
        "high": [1.5, 2.5, 3.5],
        "low": [0.5, 1.5, 2.5],
        "close": [1.2, 2.2, 3.2],
        "adj_close": [1.2, 2.2, 3.2],
        "volume": pd.array([100, 200, 300], dtype="Int64"),
    },
    index=INDEX,
)[clean.CANONICAL_COLUMNS]


def test_write_then_read_returns_identical_data():
    cache.write("yahoo", "AAPL", "1d", DF)
    out, fresh = cache.read("yahoo", "AAPL", "1d")
    pd.testing.assert_frame_equal(out, DF, check_freq=False)
    assert fresh is True


def test_read_missing_returns_none():
    out, fresh = cache.read("yahoo", "MISSING", "1d")
    assert out is None
    assert fresh is False


def test_stale_after_ttl(monkeypatch):
    cache.write("yahoo", "AAPL", "1d", DF)
    p = cache._path("yahoo", "AAPL", "1d")
    old_mtime = p.stat().st_mtime - 100_000
    import os

    os.utime(p, (old_mtime, old_mtime))
    out, fresh = cache.read("yahoo", "AAPL", "1d")
    assert out is not None
    assert fresh is False


def test_offline_returns_stale_data_without_marking_fresh_check(monkeypatch):
    cache.write("yahoo", "AAPL", "1d", DF)
    p = cache._path("yahoo", "AAPL", "1d")
    old_mtime = p.stat().st_mtime - 100_000
    import os

    os.utime(p, (old_mtime, old_mtime))
    out, fresh = cache.read("yahoo", "AAPL", "1d", offline=True)
    assert out is not None
    assert fresh is True  # offline ignores staleness


def test_write_merges_with_existing_range():
    cache.write("yahoo", "AAPL", "1d", DF.iloc[:2])
    more = pd.DataFrame(
        {
            "open": [4.0],
            "high": [4.5],
            "low": [3.5],
            "close": [4.2],
            "adj_close": [4.2],
            "volume": pd.array([400], dtype="Int64"),
        },
        index=pd.date_range("2024-01-04", periods=1, name="date"),
    )[clean.CANONICAL_COLUMNS]
    cache.write("yahoo", "AAPL", "1d", more)
    out, _ = cache.read("yahoo", "AAPL", "1d")
    assert len(out) == 3


def test_clear_removes_only_matching_ticker():
    cache.write("yahoo", "AAPL", "1d", DF)
    cache.write("yahoo", "MSFT", "1d", DF)
    cache.clear(ticker="AAPL")
    out_aapl, _ = cache.read("yahoo", "AAPL", "1d")
    out_msft, _ = cache.read("yahoo", "MSFT", "1d")
    assert out_aapl is None
    assert out_msft is not None


def test_clear_removes_all_without_ticker():
    cache.write("yahoo", "AAPL", "1d", DF)
    cache.write("yahoo", "MSFT", "1d", DF)
    cache.clear()
    assert cache.read("yahoo", "AAPL", "1d")[0] is None
    assert cache.read("yahoo", "MSFT", "1d")[0] is None
