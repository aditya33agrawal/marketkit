from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from marketkit.analytics.returns import PriceData, cagr, returns


def volatility(data: PriceData, *, periods_per_year: int = 252, **kw: Any) -> float:
    r = returns(data, **kw)
    return float(r.std(ddof=1) * np.sqrt(periods_per_year))


def sharpe(data: PriceData, *, rf: float = 0.0, periods_per_year: int = 252, **kw: Any) -> float:
    r = returns(data, **kw)
    rf_per = (1 + rf) ** (1 / periods_per_year) - 1  # annual rf -> per-period
    excess = r - rf_per
    return float((excess.mean() / r.std(ddof=1)) * np.sqrt(periods_per_year))


def downside_deviation(
    data: PriceData, *, mar: float = 0.0, periods_per_year: int = 252, **kw: Any
) -> float:
    """Annualized standard deviation of returns falling below a minimum acceptable return."""
    r = returns(data, **kw)
    mar_per = (1 + mar) ** (1 / periods_per_year) - 1
    downside = (r - mar_per).clip(upper=0)
    return float(np.sqrt((downside**2).mean()) * np.sqrt(periods_per_year))


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


def calmar(data: PriceData, *, periods_per_year: int = 252, **kw: Any) -> float:
    """CAGR divided by the absolute value of max drawdown.

    A series with no drawdown at all (monotonically non-decreasing) has no
    well-defined ratio: returns +inf/-inf/nan depending on the sign of CAGR,
    rather than raising a ZeroDivisionError.
    """
    growth_rate = cagr(data, periods_per_year=periods_per_year, **{
        k: v for k, v in kw.items() if k == "column"
    })
    _, max_dd = drawdown(data, **kw)
    if max_dd == 0:
        if growth_rate == 0:
            return float("nan")
        return float("inf") if growth_rate > 0 else float("-inf")
    return float(growth_rate / abs(max_dd))


def omega(data: PriceData, *, threshold: float = 0.0, **kw: Any) -> float:
    """Omega ratio: probability-weighted gains above a threshold vs losses below it."""
    r = returns(data, **kw)
    excess = r - threshold
    gains = excess[excess > 0].sum()
    losses = -excess[excess < 0].sum()
    return float(gains / losses)


def var(data: PriceData, *, level: float = 0.05, method: str = "historical", **kw: Any) -> float:
    """Value at Risk, returned as a positive loss magnitude.

    `method="historical"` uses the empirical return quantile;
    `method="gaussian"` assumes normally distributed returns.
    """
    r = returns(data, **kw)
    if method == "gaussian":
        z = _norm_ppf(level)
        return float(-(r.mean() + z * r.std(ddof=1)))
    return float(-r.quantile(level))


def cvar(data: PriceData, *, level: float = 0.05, **kw: Any) -> float:
    """Conditional VaR (expected shortfall): mean loss beyond the VaR threshold."""
    r = returns(data, **kw)
    threshold = r.quantile(level)
    tail = r[r <= threshold]
    return float(-tail.mean())


def ulcer_index(data: PriceData, **kw: Any) -> float:
    """Root-mean-square of percentage drawdowns -- penalizes deep, sustained drawdowns."""
    dd, _ = drawdown(data, **kw)
    return float(np.sqrt((dd**2).mean()))


def rolling_sharpe(
    data: PriceData, *, window: int = 63, rf: float = 0.0, periods_per_year: int = 252, **kw: Any
) -> pd.Series:
    """Time-varying Sharpe ratio over a rolling window."""
    r = returns(data, **kw)
    rf_per = (1 + rf) ** (1 / periods_per_year) - 1
    excess = r - rf_per
    rolling_mean = excess.rolling(window).mean()
    rolling_std = excess.rolling(window).std(ddof=1)
    return (rolling_mean / rolling_std) * np.sqrt(periods_per_year)


def rolling_volatility(data: PriceData, *, window: int = 21, periods_per_year: int = 252, **kw: Any) -> pd.Series:
    """Time-varying annualized volatility over a rolling window."""
    r = returns(data, **kw)
    return r.rolling(window).std(ddof=1) * np.sqrt(periods_per_year)


def _norm_ppf(p: float) -> float:
    """Inverse CDF of the standard normal, via Acklam's rational approximation.

    Avoids a hard `scipy` dependency for the common Gaussian-VaR case.
    """
    if not 0 < p < 1:
        raise ValueError("p must be in (0, 1)")

    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]

    p_low, p_high = 0.02425, 1 - 0.02425

    if p < p_low:
        q = np.sqrt(-2 * np.log(p))
        return float(
            (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5])
            / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
        )
    if p > p_high:
        q = np.sqrt(-2 * np.log(1 - p))
        return float(
            -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5])
            / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
        )
    q = p - 0.5
    r = q * q
    return float(
        (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q
        / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)
    )
