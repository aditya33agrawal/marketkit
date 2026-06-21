"""Boolean signal helpers. Building blocks only -- not a backtester.

These return boolean Series flagging where a condition occurs. Combine them
with your own position/sizing logic. Nothing here is financial advice.
"""

from __future__ import annotations

import pandas as pd

from marketkit.analytics.indicators import rsi, sma
from marketkit.analytics.returns import PriceData


def crossover(a: pd.Series, b: pd.Series) -> pd.Series:
    """True where `a` crosses above `b` on this bar (was <=, now >)."""
    a, b = a.align(b, join="inner")
    return (a > b) & (a.shift(1) <= b.shift(1))


def crossunder(a: pd.Series, b: pd.Series) -> pd.Series:
    """True where `a` crosses below `b` on this bar (was >=, now <)."""
    a, b = a.align(b, join="inner")
    return (a < b) & (a.shift(1) >= b.shift(1))


def golden_cross(data: PriceData, *, fast: int = 50, slow: int = 200, column: str = "close") -> pd.Series:
    """True where the fast SMA crosses above the slow SMA (a classic bullish signal)."""
    fast_sma = sma(data, window=fast, column=column)
    slow_sma = sma(data, window=slow, column=column)
    return crossover(fast_sma, slow_sma)


def death_cross(data: PriceData, *, fast: int = 50, slow: int = 200, column: str = "close") -> pd.Series:
    """True where the fast SMA crosses below the slow SMA (a classic bearish signal)."""
    fast_sma = sma(data, window=fast, column=column)
    slow_sma = sma(data, window=slow, column=column)
    return crossunder(fast_sma, slow_sma)


def rsi_oversold(data: PriceData, *, period: int = 14, threshold: float = 30.0, column: str = "close") -> pd.Series:
    """True where RSI is at/below an oversold threshold."""
    return rsi(data, period=period, column=column) <= threshold


def rsi_overbought(data: PriceData, *, period: int = 14, threshold: float = 70.0, column: str = "close") -> pd.Series:
    """True where RSI is at/above an overbought threshold."""
    return rsi(data, period=period, column=column) >= threshold
