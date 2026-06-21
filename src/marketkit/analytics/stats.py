"""Benchmark-relative and pure-statistical transforms on top of the price contract."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from marketkit.analytics.returns import PriceData, returns


def _aligned_returns(data: PriceData, benchmark: PriceData, **kw: Any) -> tuple[pd.Series, pd.Series]:
    a = returns(data, **kw)
    b = returns(benchmark, **kw)
    aligned_a, aligned_b = a.align(b, join="inner")
    return aligned_a, aligned_b


def beta(data: PriceData, benchmark: PriceData, **kw: Any) -> float:
    """Slope of asset returns regressed on benchmark returns."""
    a, b = _aligned_returns(data, benchmark, **kw)
    return float(a.cov(b) / b.var())


def alpha(
    data: PriceData,
    benchmark: PriceData,
    *,
    rf: float = 0.0,
    periods_per_year: int = 252,
    **kw: Any,
) -> float:
    """Annualized Jensen's alpha: excess return not explained by beta exposure."""
    a, b = _aligned_returns(data, benchmark, **kw)
    rf_per = (1 + rf) ** (1 / periods_per_year) - 1
    b_value = a.cov(b) / b.var()
    alpha_per_period = (a.mean() - rf_per) - b_value * (b.mean() - rf_per)
    return float((1 + alpha_per_period) ** periods_per_year - 1)


def correlation(data: PriceData, benchmark: PriceData, **kw: Any) -> float:
    a, b = _aligned_returns(data, benchmark, **kw)
    return float(a.corr(b))


def tracking_error(
    data: PriceData, benchmark: PriceData, *, periods_per_year: int = 252, **kw: Any
) -> float:
    """Annualized standard deviation of the return difference vs a benchmark."""
    a, b = _aligned_returns(data, benchmark, **kw)
    diff = a - b
    return float(diff.std(ddof=1) * np.sqrt(periods_per_year))


def information_ratio(
    data: PriceData, benchmark: PriceData, *, periods_per_year: int = 252, **kw: Any
) -> float:
    """Annualized active return divided by tracking error."""
    a, b = _aligned_returns(data, benchmark, **kw)
    diff = a - b
    te = diff.std(ddof=1) * np.sqrt(periods_per_year)
    active_return = diff.mean() * periods_per_year
    return float(active_return / te)


def rolling_beta(data: PriceData, benchmark: PriceData, *, window: int = 63, **kw: Any) -> pd.Series:
    """Time-varying beta over a rolling window."""
    a, b = _aligned_returns(data, benchmark, **kw)
    rolling_cov = a.rolling(window).cov(b)
    rolling_var = b.rolling(window).var()
    return rolling_cov / rolling_var


def zscore(data: PriceData, *, window: int | None = None, column: str = "close") -> pd.Series:
    """Standardize a price series. Rolling if `window` is given, else full-sample."""
    px = data[column] if isinstance(data, pd.DataFrame) else data
    if window is None:
        return (px - px.mean()) / px.std(ddof=1)
    mean = px.rolling(window).mean()
    std = px.rolling(window).std(ddof=1)
    return (px - mean) / std


def normalize(data: PriceData, *, base: float = 100.0, column: str = "adj_close") -> pd.Series:
    """Rebase a price series to a common starting value -- the comparison-chart helper."""
    px = data[column] if isinstance(data, pd.DataFrame) else data
    return px / px.iloc[0] * base


def autocorr(data: PriceData, *, lags: int = 20, **kw: Any) -> pd.Series:
    """Return autocorrelation at each lag from 1..lags."""
    r = returns(data, **kw)
    values = [r.autocorr(lag=lag) for lag in range(1, lags + 1)]
    return pd.Series(values, index=pd.RangeIndex(1, lags + 1, name="lag"))


def linreg_channel(data: PriceData, *, window: int = 100, k: float = 2.0, column: str = "close") -> pd.DataFrame:
    """Rolling least-squares trend line +/- k * residual std, over the trailing window."""
    px = data[column] if isinstance(data, pd.DataFrame) else data
    x = np.arange(window, dtype="float64")
    x_mean = x.mean()
    x_centered = x - x_mean
    denom = (x_centered**2).sum()

    mid = pd.Series(np.nan, index=px.index)
    std = pd.Series(np.nan, index=px.index)
    values = px.to_numpy()
    for i in range(window - 1, len(values)):
        window_vals = values[i - window + 1 : i + 1]
        slope = float(np.dot(x_centered, window_vals - window_vals.mean()) / denom)
        intercept = window_vals.mean() - slope * x_mean
        fitted = intercept + slope * x
        resid_std = float(np.std(window_vals - fitted, ddof=1))
        mid.iloc[i] = intercept + slope * x[-1]
        std.iloc[i] = resid_std

    return pd.DataFrame({"mid": mid, "upper": mid + k * std, "lower": mid - k * std})


def hurst(data: PriceData, *, max_lag: int = 100, column: str = "close") -> float:
    """Hurst exponent via rescaled-range scaling. >0.5 trending, <0.5 mean-reverting, ~0.5 random walk."""
    px = data[column] if isinstance(data, pd.DataFrame) else data
    values = px.to_numpy()
    max_lag = min(max_lag, len(values) // 2)
    lags = range(2, max_lag)
    tau = [np.std(np.subtract(values[lag:], values[:-lag])) for lag in lags]
    log_lags = np.log(list(lags))
    log_tau = np.log(tau)
    slope, _ = np.polyfit(log_lags, log_tau, 1)
    return float(slope)


def rolling_corr(frames: dict[str, PriceData] | pd.DataFrame, *, window: int = 63) -> pd.DataFrame:
    """Pairwise rolling correlation of returns across multiple tickers.

    Accepts a dict of {name: price_data} or a DataFrame of already-aligned
    return series. Returns a DataFrame with a MultiIndex column (pair, pair).
    """
    if isinstance(frames, dict):
        rets = pd.DataFrame({name: returns(df) for name, df in frames.items()})
    else:
        rets = frames

    names = list(rets.columns)
    out = {}
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            out[(a, b)] = rets[a].rolling(window).corr(rets[b])
    return pd.DataFrame(out)
