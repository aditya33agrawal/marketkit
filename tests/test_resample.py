import pandas as pd
import pytest

from marketkit import clean, fetch
from marketkit.errors import InvalidRequest


def _daily_frame():
    idx = pd.date_range("2024-01-01", periods=14)  # two full weeks
    raw = pd.DataFrame(
        {
            "Open": range(14),
            "High": [x + 1 for x in range(14)],
            "Low": [x - 1 for x in range(14)],
            "Close": [100 + i for i in range(14)],
            "Volume": [100] * 14,
        },
        index=idx,
    )
    return clean.normalize(raw, source="yahoo")


def test_resample_weekly_aggregates_ohlcv():
    df = _daily_frame()
    out = fetch.resample(df, "1wk")
    assert out["volume"].iloc[0] == pytest.approx(700.0)  # 7 days * 100
    assert out["close"].iloc[0] == df["close"].iloc[6]
    assert out["open"].iloc[0] == df["open"].iloc[0]
    assert out["high"].iloc[0] == df["high"].iloc[:7].max()
    assert out["low"].iloc[0] == df["low"].iloc[:7].min()


def test_resample_invalid_interval_raises():
    df = _daily_frame()
    with pytest.raises(InvalidRequest):
        fetch.resample(df, "1d")


def test_fetch_rejects_unsupported_interval(monkeypatch):
    with pytest.raises(InvalidRequest):
        fetch.get("AAPL", interval="3d")
