"""Registers the `df.mk` pandas accessor. Pure forwarding -- no logic lives here.

Importing this module (done once, from `marketkit/__init__.py`) registers the
accessor as a side effect; nothing needs to be imported from it directly.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from marketkit.analytics import indicators, risk, stats
from marketkit.analytics.returns import cagr, returns


@pd.api.extensions.register_dataframe_accessor("mk")
class MarketkitAccessor:
    def __init__(self, pandas_obj: pd.DataFrame) -> None:
        self._df = pandas_obj

    # returns / risk
    def returns(self, **kw: Any) -> pd.Series:
        return returns(self._df, **kw)

    def cagr(self, **kw: Any) -> float:
        return cagr(self._df, **kw)

    def volatility(self, **kw: Any) -> float:
        return risk.volatility(self._df, **kw)

    def sharpe(self, **kw: Any) -> float:
        return risk.sharpe(self._df, **kw)

    def sortino(self, **kw: Any) -> float:
        return risk.sortino(self._df, **kw)

    def drawdown(self, **kw: Any) -> tuple[pd.Series, float]:
        return risk.drawdown(self._df, **kw)

    def calmar(self, **kw: Any) -> float:
        return risk.calmar(self._df, **kw)

    def var(self, **kw: Any) -> float:
        return risk.var(self._df, **kw)

    def cvar(self, **kw: Any) -> float:
        return risk.cvar(self._df, **kw)

    # indicators
    def sma(self, **kw: Any) -> pd.Series:
        return indicators.sma(self._df, **kw)

    def ema(self, **kw: Any) -> pd.Series:
        return indicators.ema(self._df, **kw)

    def rsi(self, **kw: Any) -> pd.Series:
        return indicators.rsi(self._df, **kw)

    def macd(self, **kw: Any) -> pd.DataFrame:
        return indicators.macd(self._df, **kw)

    def bollinger(self, **kw: Any) -> pd.DataFrame:
        return indicators.bollinger(self._df, **kw)

    def atr(self, **kw: Any) -> pd.Series:
        return indicators.atr(self._df, **kw)

    # stats
    def zscore(self, **kw: Any) -> pd.Series:
        return stats.zscore(self._df, **kw)

    def normalize(self, **kw: Any) -> pd.Series:
        return stats.normalize(self._df, **kw)

    # convenience
    def summary(self) -> pd.Series:
        _, max_dd = risk.drawdown(self._df)
        return pd.Series(
            {
                "start": self._df.index[0].date(),
                "end": self._df.index[-1].date(),
                "last_close": round(self._df["close"].iloc[-1], 2),
                "cagr": round(self.cagr(), 4),
                "annual_vol": round(self.volatility(), 4),
                "sharpe": round(self.sharpe(), 2),
                "max_drawdown": round(max_dd, 4),
            }
        )

    def plot(self, **kw: Any) -> Any:
        from marketkit.plot import plot as _plot

        return _plot(self._df, **kw)
