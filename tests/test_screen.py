import sys

import pandas as pd

import marketkit.screen  # noqa: F401  (ensures sys.modules entry exists)
from marketkit import clean

# marketkit/__init__.py does `from marketkit.screen import compare, screen`, which
# rebinds the `marketkit.screen` attribute to the `screen` function -- same
# collision test_summary.py works around. Reach the submodule via sys.modules.
screen_mod = sys.modules["marketkit.screen"]


def _frame(start_close):
    idx = pd.date_range("2024-01-01", periods=30)
    raw = pd.DataFrame(
        {
            "Open": range(30),
            "High": range(30),
            "Low": range(30),
            "Close": [start_close + i for i in range(30)],
            "Volume": [100] * 30,
        },
        index=idx,
    )
    return clean.normalize(raw, source="yahoo")


def test_compare_builds_metrics_table(monkeypatch):
    frames = {"AAA": _frame(100), "BBB": _frame(50)}
    monkeypatch.setattr(screen_mod, "get", lambda ticker, **kw: frames[ticker])

    out = screen_mod.compare(["AAA", "BBB"], metrics=["cagr", "sharpe"])
    assert set(out.index) == {"AAA", "BBB"}
    assert set(out.columns) == {"cagr", "sharpe"}


def test_screen_filters_by_predicate(monkeypatch):
    frames = {"AAA": _frame(100), "BBB": _frame(50)}
    monkeypatch.setattr(screen_mod, "get", lambda ticker, **kw: frames[ticker])

    out = screen_mod.screen(["AAA", "BBB"], filters={"cagr": lambda x: x > 0})
    assert set(out.index) == {"AAA", "BBB"}  # both rising series pass

    out_none = screen_mod.screen(["AAA", "BBB"], filters={"cagr": lambda x: x > 1e9})
    assert out_none.empty
