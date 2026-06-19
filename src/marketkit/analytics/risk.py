from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from marketkit.analytics.returns import PriceData, returns


def volatility(data: PriceData, *, periods_per_year: int = 252, **kw: Any) -> float:
    r = returns(data, **kw)
    return float(r.std(ddof=1) * np.sqrt(periods_per_year))


def sharpe(data: PriceData, *, rf: float = 0.0, periods_per_year: int = 252, **kw: Any) -> float:
    r = returns(data, **kw)
    rf_per = (1 + rf) ** (1 / periods_per_year) - 1  # annual rf -> per-period
    excess = r - rf_per
    return float((excess.mean() / r.std(ddof=1)) * np.sqrt(periods_per_year))


def sortino(data: PriceData, *, rf: float = 0.0, periods_per_year: int = 252, **kw: Any) -> float:
    r = returns(data, **kw)
    rf_per = (1 + rf) ** (1 / periods_per_year) - 1
    excess = r - rf_per
    downside = excess[excess < 0].std(ddof=1)
    return float((excess.mean() / downside) * np.sqrt(periods_per_year))


def drawdown(data: PriceData, **kw: Any) -> tuple[pd.Series, float]:
    """Return (drawdown_series, max_drawdown)."""
    r = returns(data, **kw)
    curve = (1 + r).cumprod()
    peak = curve.cummax()
    dd = curve / peak - 1
    return dd, float(dd.min())
