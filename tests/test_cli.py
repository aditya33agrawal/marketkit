import sys

import pandas as pd
import pytest

import marketkit.cli  # noqa: F401  (ensures sys.modules entry exists)
from marketkit import clean
from marketkit.errors import DataUnavailable

cli_mod = sys.modules["marketkit.cli"]


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


def test_get_command_prints_dataframe(monkeypatch, capsys):
    monkeypatch.setattr(cli_mod, "get", lambda *a, **kw: _frame())
    rc = cli_mod.main(["get", "AAPL"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "close" in out


def test_get_command_writes_csv(monkeypatch, tmp_path):
    monkeypatch.setattr(cli_mod, "get", lambda *a, **kw: _frame())
    out_path = tmp_path / "out.csv"
    rc = cli_mod.main(["get", "AAPL", "--out", str(out_path)])
    assert rc == 0
    assert out_path.exists()


def test_summary_command(monkeypatch, capsys):
    monkeypatch.setattr(cli_mod, "summary", lambda ticker, **kw: pd.Series({"ticker": ticker.upper()}))
    rc = cli_mod.main(["summary", "aapl"])
    assert rc == 0
    assert "AAPL" in capsys.readouterr().out


def test_marketkit_error_returns_nonzero(monkeypatch, capsys):
    def boom(*a, **kw):
        raise DataUnavailable("no data")

    monkeypatch.setattr(cli_mod, "get", boom)
    rc = cli_mod.main(["get", "AAPL"])
    assert rc == 1
    assert "error" in capsys.readouterr().err


def test_unknown_command_raises_systemexit():
    with pytest.raises(SystemExit):
        cli_mod.main(["bogus"])


def test_plot_command_saves_to_file(monkeypatch, tmp_path):
    import matplotlib

    matplotlib.use("Agg")
    monkeypatch.setattr(cli_mod, "get", lambda *a, **kw: _frame())
    out_path = tmp_path / "chart.png"
    rc = cli_mod.main(["plot", "AAPL", "--indicators", "sma:5", "--save", str(out_path)])
    assert rc == 0
    assert out_path.exists()
