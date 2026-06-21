from __future__ import annotations

import numpy as np
import pandas as pd

from marketkit.analytics.returns import PriceData
from marketkit.errors import InvalidRequest


def _px(data: PriceData, column: str = "close") -> pd.Series:
    return data[column] if isinstance(data, pd.DataFrame) else data


def _ohlc(data: PriceData, *cols: str) -> pd.DataFrame:
    if not isinstance(data, pd.DataFrame):
        raise InvalidRequest(
            f"this indicator needs a DataFrame with columns {cols!r}, not a bare Series"
        )
    missing = [c for c in cols if c not in data.columns]
    if missing:
        raise InvalidRequest(f"missing required column(s) {missing!r}")
    return data


def sma(data: PriceData, window: int = 20, column: str = "close") -> pd.Series:
    return _px(data, column).rolling(window).mean()


def ema(data: PriceData, window: int = 20, column: str = "close") -> pd.Series:
    return _px(data, column).ewm(span=window, adjust=False).mean()


def wma(data: PriceData, window: int = 20, column: str = "close") -> pd.Series:
    """Linearly weighted moving average (most recent bar weighted highest)."""
    px = _px(data, column)
    weights = np.arange(1, window + 1, dtype="float64")

    def _w(values: np.ndarray) -> float:
        return float(np.dot(values, weights) / weights.sum())

    return px.rolling(window).apply(_w, raw=True)


def hma(data: PriceData, window: int = 20, column: str = "close") -> pd.Series:
    """Hull moving average: a low-lag MA built from weighted moving averages."""
    px = _px(data, column)
    half = max(int(window / 2), 1)
    sqrt_n = max(int(np.sqrt(window)), 1)
    wma_half = wma(px, window=half)
    wma_full = wma(px, window=window)
    raw_hma = 2 * wma_half - wma_full
    return wma(raw_hma, window=sqrt_n)


def dema(data: PriceData, window: int = 20, column: str = "close") -> pd.Series:
    """Double exponential moving average (reduced lag vs a plain EMA)."""
    px = _px(data, column)
    ema1 = ema(px, window=window)
    ema2 = ema(ema1, window=window)
    return 2 * ema1 - ema2


def tema(data: PriceData, window: int = 20, column: str = "close") -> pd.Series:
    """Triple exponential moving average."""
    px = _px(data, column)
    ema1 = ema(px, window=window)
    ema2 = ema(ema1, window=window)
    ema3 = ema(ema2, window=window)
    return 3 * ema1 - 3 * ema2 + ema3


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


def true_range(data: PriceData) -> pd.Series:
    """True range: the building block for ATR/Keltner. Needs OHLC columns."""
    df = _ohlc(data, "high", "low", "close")
    h, low, c = df["high"], df["low"], df["close"]
    prev_close = c.shift(1)
    ranges = pd.concat(
        [h - low, (h - prev_close).abs(), (low - prev_close).abs()], axis=1
    )
    return ranges.max(axis=1)


def atr(data: PriceData, period: int = 14) -> pd.Series:
    """Average True Range, Wilder-smoothed."""
    return true_range(data).ewm(alpha=1 / period, adjust=False).mean()


def stochastic(data: PriceData, k: int = 14, d: int = 3) -> pd.DataFrame:
    """Stochastic oscillator: %K and %D."""
    df = _ohlc(data, "high", "low", "close")
    low_k = df["low"].rolling(k).min()
    high_k = df["high"].rolling(k).max()
    pct_k = 100 * (df["close"] - low_k) / (high_k - low_k)
    pct_d = pct_k.rolling(d).mean()
    return pd.DataFrame({"%K": pct_k, "%D": pct_d})


def williams_r(data: PriceData, period: int = 14) -> pd.Series:
    df = _ohlc(data, "high", "low", "close")
    high_n = df["high"].rolling(period).max()
    low_n = df["low"].rolling(period).min()
    return -100 * (high_n - df["close"]) / (high_n - low_n)


def cci(data: PriceData, period: int = 20) -> pd.Series:
    """Commodity Channel Index."""
    df = _ohlc(data, "high", "low", "close")
    typical = (df["high"] + df["low"] + df["close"]) / 3
    sma_tp = typical.rolling(period).mean()
    mean_dev = typical.rolling(period).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
    return (typical - sma_tp) / (0.015 * mean_dev)


def adx(data: PriceData, period: int = 14) -> pd.DataFrame:
    """Average Directional Index: adx, +di, -di. Wilder-smoothed throughout."""
    df = _ohlc(data, "high", "low", "close")
    up_move = df["high"].diff()
    down_move = -df["low"].diff()

    plus_dm = pd.Series(
        np.where((up_move > down_move) & (up_move > 0), up_move, 0.0), index=df.index
    )
    minus_dm = pd.Series(
        np.where((down_move > up_move) & (down_move > 0), down_move, 0.0), index=df.index
    )

    tr = true_range(df)
    atr_smooth = tr.ewm(alpha=1 / period, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1 / period, adjust=False).mean() / atr_smooth
    minus_di = 100 * minus_dm.ewm(alpha=1 / period, adjust=False).mean() / atr_smooth

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    adx_line = dx.ewm(alpha=1 / period, adjust=False).mean()
    return pd.DataFrame({"adx": adx_line, "+di": plus_di, "-di": minus_di})


def roc(data: PriceData, period: int = 12, column: str = "close") -> pd.Series:
    """Rate of change, in percent."""
    px = _px(data, column)
    return 100 * (px / px.shift(period) - 1)


def momentum(data: PriceData, period: int = 12, column: str = "close") -> pd.Series:
    px = _px(data, column)
    return px - px.shift(period)


def obv(data: PriceData) -> pd.Series:
    """On-Balance Volume. Needs close + volume columns."""
    df = _ohlc(data, "close", "volume")
    direction = np.sign(df["close"].diff().fillna(0))
    return (direction * df["volume"]).cumsum()


def vwap(data: PriceData) -> pd.Series:
    """Volume-weighted average price (cumulative, from the start of the frame)."""
    df = _ohlc(data, "high", "low", "close", "volume")
    typical = (df["high"] + df["low"] + df["close"]) / 3
    cum_vol = df["volume"].cumsum()
    cum_vol_px = (typical * df["volume"]).cumsum()
    return cum_vol_px / cum_vol


def mfi(data: PriceData, period: int = 14) -> pd.Series:
    """Money Flow Index."""
    df = _ohlc(data, "high", "low", "close", "volume")
    typical = (df["high"] + df["low"] + df["close"]) / 3
    raw_flow = typical * df["volume"]
    direction = typical.diff()

    pos_flow = raw_flow.where(direction > 0, 0.0)
    neg_flow = raw_flow.where(direction < 0, 0.0)

    pos_sum = pos_flow.rolling(period).sum()
    neg_sum = neg_flow.rolling(period).sum()
    ratio = pos_sum / neg_sum
    return 100 - 100 / (1 + ratio)


def keltner(data: PriceData, window: int = 20, k: int = 2, column: str = "close") -> pd.DataFrame:
    """Keltner channels: EMA midline +/- k * ATR."""
    mid = ema(data, window=window, column=column)
    band = k * atr(data, period=window)
    return pd.DataFrame({"mid": mid, "upper": mid + band, "lower": mid - band})


def donchian(data: PriceData, window: int = 20) -> pd.DataFrame:
    """Donchian channels: rolling highest-high / lowest-low."""
    df = _ohlc(data, "high", "low")
    upper = df["high"].rolling(window).max()
    lower = df["low"].rolling(window).min()
    mid = (upper + lower) / 2
    return pd.DataFrame({"upper": upper, "mid": mid, "lower": lower})


def ichimoku(
    data: PriceData,
    *,
    tenkan: int = 9,
    kijun: int = 26,
    senkou_b: int = 52,
) -> pd.DataFrame:
    """Ichimoku Kinko Hyo: tenkan-sen, kijun-sen, senkou span A/B, chikou span."""
    df = _ohlc(data, "high", "low", "close")
    high, low, close = df["high"], df["low"], df["close"]

    tenkan_sen = (high.rolling(tenkan).max() + low.rolling(tenkan).min()) / 2
    kijun_sen = (high.rolling(kijun).max() + low.rolling(kijun).min()) / 2
    senkou_a = ((tenkan_sen + kijun_sen) / 2).shift(kijun)
    senkou_b_line = ((high.rolling(senkou_b).max() + low.rolling(senkou_b).min()) / 2).shift(kijun)
    chikou_span = close.shift(-kijun)

    return pd.DataFrame(
        {
            "tenkan_sen": tenkan_sen,
            "kijun_sen": kijun_sen,
            "senkou_span_a": senkou_a,
            "senkou_span_b": senkou_b_line,
            "chikou_span": chikou_span,
        }
    )


def psar(data: PriceData, step: float = 0.02, max_step: float = 0.2) -> pd.Series:
    """Parabolic SAR (stop-and-reverse trend indicator)."""
    df = _ohlc(data, "high", "low")
    high, low = df["high"].to_numpy(), df["low"].to_numpy()
    n = len(df)
    out = np.full(n, np.nan)
    if n == 0:
        return pd.Series(out, index=df.index)

    bullish = True
    af = step
    ep = high[0]
    sar = low[0]
    out[0] = sar

    for i in range(1, n):
        prev_sar = sar
        sar = prev_sar + af * (ep - prev_sar)

        if bullish:
            sar = min(sar, low[i - 1], low[i - 2] if i > 1 else low[i - 1])
            if low[i] < sar:
                bullish = False
                sar = ep
                ep = low[i]
                af = step
        else:
            sar = max(sar, high[i - 1], high[i - 2] if i > 1 else high[i - 1])
            if high[i] > sar:
                bullish = True
                sar = ep
                ep = high[i]
                af = step

        if bullish and high[i] > ep:
            ep = high[i]
            af = min(af + step, max_step)
        elif not bullish and low[i] < ep:
            ep = low[i]
            af = min(af + step, max_step)

        out[i] = sar

    return pd.Series(out, index=df.index)
