from __future__ import annotations

import numpy as np

from marketkit.analytics.returns import returns


def volatility(data, *, periods_per_year=252, **kw):
    r = returns(data, **kw)
    return r.std(ddof=1) * np.sqrt(periods_per_year)


def sharpe(data, *, rf=0.0, periods_per_year=252, **kw):
    r = returns(data, **kw)
    rf_per = (1 + rf) ** (1 / periods_per_year) - 1  # annual rf -> per-period
    excess = r - rf_per
    return (excess.mean() / r.std(ddof=1)) * np.sqrt(periods_per_year)


def sortino(data, *, rf=0.0, periods_per_year=252, **kw):
    r = returns(data, **kw)
    rf_per = (1 + rf) ** (1 / periods_per_year) - 1
    excess = r - rf_per
    downside = excess[excess < 0].std(ddof=1)
    return (excess.mean() / downside) * np.sqrt(periods_per_year)


def drawdown(data, **kw):
    """Return (drawdown_series, max_drawdown)."""
    r = returns(data, **kw)
    curve = (1 + r).cumprod()
    peak = curve.cummax()
    dd = curve / peak - 1
    return dd, dd.min()
