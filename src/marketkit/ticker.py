"""A thin, discoverable object wrapper around a fetched ticker's frame.

The functional API (`mk.get`, `mk.rsi`, ...) is first-class; `Ticker` exists
for people who'd rather tab-complete a single object than re-pass a `df`
to every call.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from marketkit.analytics import indicators, risk
from marketkit.analytics.returns import cagr, returns
from marketkit.fetch import get


class Ticker:
    """Fetches once on construction; every method operates on the cached frame."""

    def __init__(self, symbol: str, *, period: str = "1y", **kw: Any) -> None:
        self.symbol = symbol.upper()
        self.df: pd.DataFrame = get(symbol, period=period, **kw)

    def __repr__(self) -> str:
        return f"Ticker({self.symbol!r}, rows={len(self.df)})"

    # -- analytics, forwarded onto the cached frame --
    def returns(self, **kw: Any) -> pd.Series:
        return returns(self.df, **kw)

    def cagr(self, **kw: Any) -> float:
        return cagr(self.df, **kw)

    def volatility(self, **kw: Any) -> float:
        return risk.volatility(self.df, **kw)

    def sharpe(self, **kw: Any) -> float:
        return risk.sharpe(self.df, **kw)

    def sortino(self, **kw: Any) -> float:
        return risk.sortino(self.df, **kw)

    def drawdown(self, **kw: Any) -> tuple[pd.Series, float]:
        return risk.drawdown(self.df, **kw)

    def sma(self, **kw: Any) -> pd.Series:
        return indicators.sma(self.df, **kw)

    def ema(self, **kw: Any) -> pd.Series:
        return indicators.ema(self.df, **kw)

    def rsi(self, **kw: Any) -> pd.Series:
        return indicators.rsi(self.df, **kw)

    def macd(self, **kw: Any) -> pd.DataFrame:
        return indicators.macd(self.df, **kw)

    def bollinger(self, **kw: Any) -> pd.DataFrame:
        return indicators.bollinger(self.df, **kw)

    def summary(self) -> pd.Series:
        _, max_dd = risk.drawdown(self.df)
        return pd.Series(
            {
                "ticker": self.symbol,
                "start": self.df.index[0].date(),
                "end": self.df.index[-1].date(),
                "last_close": round(self.df["close"].iloc[-1], 2),
                "cagr": round(self.cagr(), 4),
                "annual_vol": round(self.volatility(), 4),
                "sharpe": round(self.sharpe(), 2),
                "max_drawdown": round(max_dd, 4),
            }
        )

    def plot(self, **kw: Any) -> Any:
        from marketkit.plot import plot as _plot

        return _plot(self.df, **kw)
