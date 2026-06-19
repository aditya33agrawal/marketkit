from __future__ import annotations

import pandas as pd

from marketkit.analytics.returns import PriceData


def _px(data: PriceData, column: str = "close") -> pd.Series:
    return data[column] if isinstance(data, pd.DataFrame) else data


def sma(data: PriceData, window: int = 20, column: str = "close") -> pd.Series:
    return _px(data, column).rolling(window).mean()


def ema(data: PriceData, window: int = 20, column: str = "close") -> pd.Series:
    return _px(data, column).ewm(span=window, adjust=False).mean()


def rsi(data: PriceData, period: int = 14, column: str = "close") -> pd.Series:
    px = _px(data, column)
    delta = px.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()  # Wilder
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - 100 / (1 + rs)


def macd(
    data: PriceData, fast: int = 12, slow: int = 26, signal: int = 9, column: str = "close"
) -> pd.DataFrame:
    px = _px(data, column)
    macd_line = ema(px, fast) - ema(px, slow)
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return pd.DataFrame({"macd": macd_line, "signal": signal_line, "hist": hist})


def bollinger(data: PriceData, window: int = 20, k: int = 2, column: str = "close") -> pd.DataFrame:
    px = _px(data, column)
    mid = px.rolling(window).mean()
    std = px.rolling(window).std(ddof=0)
    return pd.DataFrame({"mid": mid, "upper": mid + k * std, "lower": mid - k * std})
