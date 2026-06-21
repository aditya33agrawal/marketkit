import sys

import matplotlib
import pandas as pd

matplotlib.use("Agg")

import marketkit.report  # noqa: F401  (ensures sys.modules entry exists)
from marketkit import clean

report_mod = sys.modules["marketkit.report"]


def _frame():
    idx = pd.date_range("2024-01-01", periods=120)
    raw = pd.DataFrame(
        {
            "Open": range(120),
            "High": range(120),
            "Low": range(120),
            "Close": [100 + i * 0.5 for i in range(120)],
            "Volume": [100] * 120,
        },
        index=idx,
    )
    return clean.normalize(raw, source="yahoo")


def test_report_returns_figure_and_metrics(monkeypatch):
    monkeypatch.setattr(report_mod, "get", lambda *a, **kw: _frame())
    monkeypatch.setattr(report_mod, "summary", lambda ticker, **kw: pd.Series({"ticker": ticker.upper()}))

    fig, metrics = report_mod.report("aapl")
    assert len(fig.axes) == 4
    assert metrics["ticker"] == "AAPL"
