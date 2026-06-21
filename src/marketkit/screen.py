"""Compare and filter a universe of tickers by headline metrics."""

from __future__ import annotations

from typing import Any, Callable

import pandas as pd

from marketkit.analytics.returns import cagr
from marketkit.analytics.risk import drawdown, sharpe, sortino, volatility
from marketkit.fetch import get

_METRICS: dict[str, Callable[[pd.DataFrame], float]] = {
    "cagr": cagr,
    "volatility": volatility,
    "sharpe": sharpe,
    "sortino": sortino,
    "max_drawdown": lambda df: drawdown(df)[1],
}


def compare(
    tickers: list[str],
    *,
    metrics: list[str] | None = None,
    period: str = "1y",
    **kw: Any,
) -> pd.DataFrame:
    """Fetch each ticker and build a side-by-side metrics table.

    `metrics` defaults to ["cagr", "volatility", "sharpe", "max_drawdown"].
    """
    metric_names = metrics or ["cagr", "volatility", "sharpe", "max_drawdown"]
    rows: dict[str, dict[str, float]] = {}
    for ticker in tickers:
        df = get(ticker, period=period, **kw)
        rows[ticker.upper()] = {name: _METRICS[name](df) for name in metric_names}
    return pd.DataFrame(rows).T


def screen(
    tickers: list[str],
    *,
    filters: dict[str, Callable[[float], bool]],
    period: str = "1y",
    **kw: Any,
) -> pd.DataFrame:
    """Filter a universe by metric thresholds.

    `filters` maps a metric name (see `compare`'s metric table) to a predicate,
    e.g. `{"sharpe": lambda x: x > 1, "max_drawdown": lambda x: x > -0.2}`.
    Returns the `compare()` table restricted to rows passing every predicate.
    """
    table = compare(tickers, metrics=list(filters.keys()), period=period, **kw)
    mask = pd.Series(True, index=table.index)
    for name, predicate in filters.items():
        mask &= table[name].apply(predicate)
    return table[mask]
