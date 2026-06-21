import matplotlib

matplotlib.use("Agg")  # headless backend for CI

import builtins
import sys

import pandas as pd
import pytest

import marketkit.plot  # noqa: F401  (ensures sys.modules entry exists)
from marketkit.errors import PlottingUnavailable

# marketkit/__init__.py does `from marketkit.plot import plot`, which rebinds
# the `marketkit.plot` attribute to the function -- same collision test_summary.py
# already works around. Reach the submodule via sys.modules instead.
plot_mod = sys.modules["marketkit.plot"]

CLOSES = [100, 102, 101, 105, 103, 108, 104, 110, 107, 112, 109, 115, 118, 116, 120]


@pytest.fixture
def df():
    idx = pd.date_range("2024-01-01", periods=len(CLOSES))
    close = pd.Series(CLOSES, index=idx, dtype="float64")
    return pd.DataFrame(
        {
            "open": close.shift(1).fillna(close.iloc[0]),
            "high": close + 1,
            "low": close - 1,
            "close": close,
            "adj_close": close,
            "volume": pd.Series([1000] * len(CLOSES), index=idx),
        }
    )


def test_plot_line_returns_axes_with_one_line(df):
    ax = plot_mod.plot(df, column="close")
    assert len(ax.lines) == 1


def test_plot_with_overlay_indicators_adds_lines(df):
    ax = plot_mod.plot(df, column="close", indicators=["sma:5", "ema:5"])
    assert len(ax.lines) == 3  # price + sma + ema


def test_candlestick_returns_axes(df):
    ax = plot_mod.candlestick(df, volume=False)
    assert len(ax.patches) > 0  # candle bodies drawn as bars


def test_candlestick_with_volume_adds_twin_axis(df):
    ax = plot_mod.candlestick(df, volume=True)
    assert len(ax.figure.axes) == 2


def test_plot_indicators_stacks_panels(df):
    axes = plot_mod.plot_indicators(df, ["sma:5", "rsi"])
    assert isinstance(axes, list)
    assert len(axes) == 2  # price panel + rsi panel


def test_plot_indicators_overlay_only_returns_single_axes(df):
    ax = plot_mod.plot_indicators(df, ["sma:5", "ema:5"])
    assert not isinstance(ax, list)


def test_plot_drawdown_returns_axes(df):
    ax = plot_mod.plot_drawdown(df, column="close")
    assert ax is not None
    assert len(ax.lines) == 1


def test_plot_returns_histogram(df):
    ax = plot_mod.plot_returns(df, kind="hist", column="close")
    assert len(ax.patches) > 0


def test_plot_returns_cumulative(df):
    ax = plot_mod.plot_returns(df, kind="cumulative", column="close")
    assert len(ax.lines) == 1


def test_plot_returns_bad_kind_raises(df):
    from marketkit.errors import InvalidRequest

    with pytest.raises(InvalidRequest):
        plot_mod.plot_returns(df, kind="nonsense")


def test_plot_correlation_from_dict(df):
    other = df.copy()
    other["close"] = df["close"] * 1.1
    ax = plot_mod.plot_correlation({"a": df, "b": other})
    assert ax.images  # heatmap drawn via imshow


def test_plot_multi_ticker_rebase(df):
    long_a = df.copy()
    long_a["ticker"] = "A"
    long_b = df.copy()
    long_b["close"] = df["close"] * 2
    long_b["ticker"] = "B"
    long_df = pd.concat([long_a, long_b])

    ax = plot_mod.plot(long_df, column="close", rebase=True)
    assert len(ax.lines) == 2


def test_plotting_unavailable_when_matplotlib_missing(monkeypatch):
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "matplotlib.pyplot" or name.startswith("matplotlib"):
            raise ImportError("simulated missing matplotlib")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(PlottingUnavailable):
        plot_mod._mpl()


def test_plot_unknown_backend_raises(df):
    from marketkit.errors import InvalidRequest

    with pytest.raises(InvalidRequest):
        plot_mod.plot(df, backend="bogus")


def test_plotly_backend_line(df):
    fig = plot_mod.plot(df, column="close", backend="plotly")
    assert len(fig.data) == 1


def test_plotly_backend_candlestick(df):
    fig = plot_mod.plot(df, kind="candle", backend="plotly")
    assert len(fig.data) == 1
    assert fig.data[0].type == "candlestick"


def test_plotly_backend_with_indicators(df):
    fig = plot_mod.plot(df, column="close", indicators=["sma:5"], backend="plotly")
    assert len(fig.data) == 2


def test_plotly_unavailable_when_missing(monkeypatch):
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name.startswith("plotly"):
            raise ImportError("simulated missing plotly")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(PlottingUnavailable):
        plot_mod._plotly()
