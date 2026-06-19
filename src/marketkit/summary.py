from __future__ import annotations

import pandas as pd

from marketkit.analytics.returns import cagr
from marketkit.analytics.risk import drawdown, sharpe, volatility
from marketkit.fetch import get


def summary(ticker, *, period="1y", **kw):
    df = get(ticker, period=period, **kw)
    _, max_dd = drawdown(df)
    return pd.Series(
        {
            "ticker": ticker.upper(),
            "start": df.index[0].date(),
            "end": df.index[-1].date(),
            "last_close": round(df["close"].iloc[-1], 2),
            "cagr": round(cagr(df), 4),
            "annual_vol": round(volatility(df), 4),
            "sharpe": round(sharpe(df), 2),
            "max_drawdown": round(max_dd, 4),
        }
    )
