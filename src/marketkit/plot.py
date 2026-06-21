"""Charting on top of the canonical OHLCV contract.

Requires the optional `matplotlib` dependency: `pip install marketkit[plot]`.
Every function here is a thin, opinionated layer over matplotlib — it never
calls `plt.show()` (that's the caller's job) and it always returns the `Axes`
it drew on so callers can keep customizing or saving the figure.
"""

from __future__ import annotations

from typing import Any, Sequence

import pandas as pd

from marketkit.analytics.returns import PriceData
from marketkit.errors import InvalidRequest, PlottingUnavailable

# Indicators that share the price's own scale and overlay directly on it.
_OVERLAY_INDICATORS = {
    "sma", "ema", "wma", "hma", "dema", "tema", "bollinger", "keltner",
    "donchian", "vwap", "psar", "ichimoku",
}
# Indicators that need their own panel (different scale than price).
_PANEL_INDICATORS = {
    "rsi", "macd", "stochastic", "adx", "cci", "williams_r", "obv", "mfi",
    "roc", "momentum", "atr",
}


def _mpl() -> Any:
    try:
        import matplotlib.pyplot as plt
    except ImportError as e:  # pragma: no cover - exercised via monkeypatch in tests
        raise PlottingUnavailable(
            "Plotting needs matplotlib — install with `pip install marketkit[plot]`."
        ) from e
    return plt


def _parse_spec(spec: str) -> tuple[str, dict[str, Any]]:
    """Parse "name:param" (e.g. "sma:50", "macd:12,26,9") into (name, kwargs)."""
    name, _, param_str = spec.partition(":")
    name = name.strip().lower()
    if not param_str:
        return name, {}

    params = [p.strip() for p in param_str.split(",")]
    _param_names = {
        "sma": ["window"], "ema": ["window"], "wma": ["window"], "hma": ["window"],
        "dema": ["window"], "tema": ["window"],
        "bollinger": ["window", "k"], "keltner": ["window", "k"],
        "donchian": ["window"],
        "rsi": ["period"], "atr": ["period"], "cci": ["period"], "mfi": ["period"],
        "williams_r": ["period"], "roc": ["period"], "momentum": ["period"],
        "stochastic": ["k", "d"], "adx": ["period"],
        "macd": ["fast", "slow", "signal"],
    }
    names = _param_names.get(name, [])
    kwargs: dict[str, Any] = {}
    for key, value in zip(names, params):
        kwargs[key] = float(value) if "." in value else int(value)
    return name, kwargs


def _indicator_func(name: str) -> Any:
    from marketkit.analytics import indicators as ind

    if not hasattr(ind, name):
        raise InvalidRequest(f"unknown indicator '{name}'")
    return getattr(ind, name)


def _is_multi_ticker(data: pd.DataFrame) -> bool:
    return isinstance(data, pd.DataFrame) and (
        "ticker" in data.columns or isinstance(data.columns, pd.MultiIndex)
    )


def plot(
    data: PriceData,
    *,
    kind: str = "line",
    column: str = "adj_close",
    indicators: Sequence[str] | None = None,
    ax: Any = None,
    rebase: bool = False,
    backend: str = "matplotlib",
    **kw: Any,
) -> Any:
    """The one-liner price chart. Line or candlestick, with optional indicator overlays.

    `backend="plotly"` returns an interactive Plotly figure instead (needs the
    optional `[plotly]` extra); the matplotlib backend stays the default.
    """
    if backend == "plotly":
        return _plot_plotly(data, kind=kind, column=column, indicators=indicators, **kw)
    if backend != "matplotlib":
        raise InvalidRequest(f"unknown backend '{backend}' (expected 'matplotlib' or 'plotly')")

    plt = _mpl()
    if ax is None:
        _, ax = plt.subplots(figsize=(10, 5))

    if kind == "candle":
        return candlestick(data, ax=ax, **kw)

    if isinstance(data, pd.DataFrame) and _is_multi_ticker(data):
        _plot_multi_ticker(ax, data, column=column, rebase=rebase)
    else:
        ax.plot(data.index, _series(data, column), label=column)

    if indicators:
        plot_indicators(data, indicators, ax=ax)

    ax.set_xlabel("date")
    ax.legend()
    return ax


def _series(data: PriceData, column: str) -> pd.Series:
    return data[column] if isinstance(data, pd.DataFrame) else data


def _plotly() -> Any:
    try:
        import plotly.graph_objects as go
    except ImportError as e:  # pragma: no cover - exercised via monkeypatch in tests
        raise PlottingUnavailable(
            "The plotly backend needs plotly — install with `pip install marketkit[plotly]`."
        ) from e
    return go


def _plot_plotly(
    data: PriceData,
    *,
    kind: str,
    column: str,
    indicators: Sequence[str] | None,
    **kw: Any,
) -> Any:
    go = _plotly()
    fig = go.Figure()

    if kind == "candle":
        fig.add_trace(
            go.Candlestick(
                x=data.index, open=data["open"], high=data["high"],
                low=data["low"], close=data["close"], name="price",
            )
        )
    else:
        fig.add_trace(go.Scatter(x=data.index, y=_series(data, column), mode="lines", name=column))

    for spec in indicators or []:
        name, params = _parse_spec(spec)
        func = _indicator_func(name)
        out = func(data, **params)
        if isinstance(out, pd.DataFrame):
            for col in out.columns:
                fig.add_trace(go.Scatter(x=out.index, y=out[col], mode="lines", name=f"{name}.{col}"))
        else:
            fig.add_trace(go.Scatter(x=out.index, y=out.values, mode="lines", name=spec))

    fig.update_layout(xaxis_title="date")
    return fig


def _plot_multi_ticker(
    ax: Any, data: pd.DataFrame, *, column: str, rebase: bool
) -> None:
    if isinstance(data.columns, pd.MultiIndex):
        prices = data[column]
        tickers = list(prices.columns)
        for ticker in tickers:
            series = prices[ticker].dropna()
            if rebase and not series.empty:
                series = series / series.iloc[0] * 100
            ax.plot(series.index, series.values, label=ticker)
    else:
        for ticker, group in data.groupby("ticker"):
            series = group[column]
            if rebase and not series.empty:
                series = series / series.iloc[0] * 100
            ax.plot(series.index, series.values, label=ticker)


def candlestick(
    data: pd.DataFrame,
    *,
    volume: bool = True,
    ax: Any = None,
    up_color: str = "tab:green",
    down_color: str = "tab:red",
) -> Any:
    """OHLC candlestick chart, drawn with bare matplotlib primitives."""
    plt = _mpl()
    if ax is None:
        _, ax = plt.subplots(figsize=(10, 5))

    width = 0.6
    up = data["close"] >= data["open"]
    for is_up, color in ((True, up_color), (False, down_color)):
        subset = data[up == is_up]
        if subset.empty:
            continue
        ax.vlines(subset.index, subset["low"], subset["high"], color=color, linewidth=1)
        ax.bar(
            subset.index,
            (subset["close"] - subset["open"]).abs().clip(lower=1e-9),
            width,
            bottom=subset[["open", "close"]].min(axis=1),
            color=color,
        )
    ax.set_xlabel("date")

    if volume and "volume" in data.columns:
        vol_ax = ax.twinx()
        vol_ax.bar(data.index, data["volume"], width, alpha=0.2, color="gray")
        vol_ax.set_ylabel("volume")
        vol_ax.set_ylim(0, data["volume"].max() * 4)

    return ax


def plot_indicators(
    data: PriceData, indicators: Sequence[str], *, ax: Any = None
) -> Any:
    """Overlay/stack named indicators (e.g. ["sma:50", "ema:20", "bollinger", "rsi"]).

    Overlay indicators (SMA, EMA, Bollinger, ...) draw on the price axis.
    Panel indicators (RSI, MACD, ...) each get their own stacked sub-axis below
    it, sharing the x-axis. If `ax` is given, panel indicators draw on it too
    (no new axes are created once the caller has taken control of layout).
    """
    plt = _mpl()
    overlay_specs = []
    panel_names: list[str] = []
    for spec in indicators:
        name, _ = _parse_spec(spec)
        if name in _PANEL_INDICATORS:
            panel_names.append(spec)
        else:
            overlay_specs.append(spec)

    if ax is not None:
        for spec in overlay_specs:
            _draw_overlay(ax, data, spec)
        for spec in panel_names:
            _draw_panel(ax, data, spec)
        ax.legend()
        return ax

    if not panel_names:
        _, price_ax = plt.subplots(figsize=(10, 5))
        price_ax.plot(data.index, _series(data, "close"), label="close")
        for spec in overlay_specs:
            _draw_overlay(price_ax, data, spec)
        price_ax.legend()
        return price_ax

    fig, axes = plt.subplots(
        nrows=1 + len(panel_names),
        ncols=1,
        sharex=True,
        figsize=(10, 4 + 2 * len(panel_names)),
        gridspec_kw={"height_ratios": [3] + [1] * len(panel_names)},
    )
    price_ax = axes[0]
    price_ax.plot(data.index, _series(data, "close"), label="close")
    for spec in overlay_specs:
        _draw_overlay(price_ax, data, spec)
    price_ax.legend()

    for panel_ax, spec in zip(axes[1:], panel_names):
        _draw_panel(panel_ax, data, spec)

    fig.tight_layout()
    return list(axes)


def _draw_overlay(ax: Any, data: PriceData, spec: str) -> None:
    name, kwargs = _parse_spec(spec)
    func = _indicator_func(name)
    out = func(data, **kwargs)
    if isinstance(out, pd.DataFrame):
        for col in out.columns:
            ax.plot(out.index, out[col], label=f"{name}.{col}", linewidth=1)
    else:
        ax.plot(out.index, out.values, label=spec, linewidth=1)


def _draw_panel(ax: Any, data: PriceData, spec: str) -> None:
    name, kwargs = _parse_spec(spec)
    func = _indicator_func(name)
    out = func(data, **kwargs)
    if isinstance(out, pd.DataFrame):
        for col in out.columns:
            ax.plot(out.index, out[col], label=f"{name}.{col}", linewidth=1)
    else:
        ax.plot(out.index, out.values, label=spec, linewidth=1)
    ax.set_ylabel(name)
    ax.legend()


def plot_drawdown(data: PriceData, *, ax: Any = None, **kw: Any) -> Any:
    """Underwater (drawdown) curve."""
    from marketkit.analytics.risk import drawdown

    plt = _mpl()
    if ax is None:
        _, ax = plt.subplots(figsize=(10, 3))

    dd, _ = drawdown(data, **kw)
    ax.fill_between(dd.index, dd.values, 0, color="tab:red", alpha=0.4)
    ax.plot(dd.index, dd.values, color="tab:red", linewidth=1)
    ax.set_ylabel("drawdown")
    ax.set_xlabel("date")
    return ax


def plot_returns(data: PriceData, *, kind: str = "hist", ax: Any = None, **kw: Any) -> Any:
    """Returns distribution histogram, or cumulative-growth line."""
    from marketkit.analytics.returns import returns

    plt = _mpl()
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 5))

    r = returns(data, **kw)
    if kind == "hist":
        ax.hist(r.values, bins=50)
        ax.set_xlabel("return")
        ax.set_ylabel("frequency")
    elif kind == "cumulative":
        growth = (1 + r).cumprod()
        ax.plot(growth.index, growth.values)
        ax.set_ylabel("cumulative growth")
        ax.set_xlabel("date")
    else:
        raise InvalidRequest(f"unknown kind '{kind}' (expected 'hist' or 'cumulative')")
    return ax


def plot_correlation(frames: dict[str, PriceData] | pd.DataFrame, *, ax: Any = None) -> Any:
    """Correlation heatmap across multiple tickers' returns."""
    from marketkit.analytics.returns import returns

    plt = _mpl()
    if ax is None:
        _, ax = plt.subplots(figsize=(6, 6))

    if isinstance(frames, dict):
        rets = pd.DataFrame({name: returns(df) for name, df in frames.items()})
    else:
        rets = frames

    corr = rets.corr()
    im = ax.imshow(corr.values, vmin=-1, vmax=1, cmap="coolwarm")
    ax.set_xticks(range(len(corr.columns)))
    ax.set_xticklabels(corr.columns, rotation=45, ha="right")
    ax.set_yticks(range(len(corr.index)))
    ax.set_yticklabels(corr.index)
    ax.figure.colorbar(im, ax=ax)
    return ax
