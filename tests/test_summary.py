import sys

import pandas as pd

from marketkit import clean, fetch
import marketkit.summary  # noqa: F401  (ensures sys.modules entry exists)

summary_mod = sys.modules["marketkit.summary"]


def _frame():
    idx = pd.date_range("2024-01-01", periods=10)
    raw = pd.DataFrame(
        {
            "Open": range(10),
            "High": range(10),
            "Low": range(10),
            "Close": [100 + i for i in range(10)],
            "Volume": [100] * 10,
        },
        index=idx,
    )
    return clean.normalize(raw, source="yahoo")


def test_summary_shape(monkeypatch):
    monkeypatch.setattr(fetch, "get", lambda *a, **kw: _frame())
    monkeypatch.setattr(summary_mod, "get", lambda *a, **kw: _frame())

    out = summary_mod.summary("aapl")

    assert out["ticker"] == "AAPL"
    assert set(
        ["ticker", "start", "end", "last_close", "cagr", "annual_vol", "sharpe", "max_drawdown"]
    ) == set(out.index)
