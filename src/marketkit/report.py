"""One-call multi-panel tear sheet: price+MAs, drawdown, returns histogram, rolling Sharpe."""

from __future__ import annotations

from typing import Any

import pandas as pd

from marketkit.analytics.indicators import sma
from marketkit.analytics.risk import drawdown, rolling_sharpe
from marketkit.analytics.returns import returns
from marketkit.errors import PlottingUnavailable
from marketkit.fetch import get
from marketkit.summary import summary


def report(ticker: str, *, period: str = "1y", **kw: Any) -> tuple[Any, pd.Series]:
    """Fetch `ticker`, render a tear-sheet figure, and return `(figure, metrics)`.

    Requires the `[plot]` extra. Not financial advice -- a quick-look diagnostic.
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError as e:
        raise PlottingUnavailable(
            "report() needs matplotlib — install with `pip install marketkit[plot]`."
        ) from e

    df = get(ticker, period=period, **kw)
    metrics = summary(ticker, period=period, **kw)

    fig, axes = plt.subplots(4, 1, figsize=(10, 14), sharex=False)

    axes[0].plot(df.index, df["adj_close"], label="adj_close")
    axes[0].plot(df.index, sma(df, window=20, column="adj_close"), label="sma:20", linewidth=1)
    axes[0].plot(df.index, sma(df, window=50, column="adj_close"), label="sma:50", linewidth=1)
    axes[0].set_title(f"{metrics['ticker']} price")
    axes[0].legend()

    dd, _ = drawdown(df)
    axes[1].fill_between(dd.index, dd.values, 0, color="tab:red", alpha=0.4)
    axes[1].set_title("drawdown")

    r = returns(df)
    axes[2].hist(r.values, bins=50)
    axes[2].set_title("daily returns distribution")

    rs = rolling_sharpe(df, window=63)
    axes[3].plot(rs.index, rs.values)
    axes[3].axhline(0, color="black", linewidth=0.5)
    axes[3].set_title("rolling 63-day Sharpe")

    fig.tight_layout()
    return fig, metrics
