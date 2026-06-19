from __future__ import annotations

import pandas as pd


def _px(data, column="close"):
    return data[column] if isinstance(data, pd.DataFrame) else data


def sma(data, window=20, column="close"):
    return _px(data, column).rolling(window).mean()


def ema(data, window=20, column="close"):
    return _px(data, column).ewm(span=window, adjust=False).mean()


def rsi(data, period=14, column="close"):
    px = _px(data, column)
    delta = px.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()  # Wilder
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - 100 / (1 + rs)


def macd(data, fast=12, slow=26, signal=9, column="close"):
    px = _px(data, column)
    macd_line = ema(px, fast) - ema(px, slow)
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return pd.DataFrame({"macd": macd_line, "signal": signal_line, "hist": hist})


def bollinger(data, window=20, k=2, column="close"):
    px = _px(data, column)
    mid = px.rolling(window).mean()
    std = px.rolling(window).std(ddof=0)
    return pd.DataFrame({"mid": mid, "upper": mid + k * std, "lower": mid - k * std})
