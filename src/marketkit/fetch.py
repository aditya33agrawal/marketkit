from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pandas as pd

from marketkit import cache, clean, config
from marketkit import sources as _sources  # noqa: F401  (registers built-in sources)
from marketkit.errors import DataUnavailable, InvalidRequest, RateLimited, SourceError
from marketkit.sources.base import get_source

_PERIOD_YEARS = {"1y": 1, "2y": 2, "5y": 5, "10y": 10, "max": 50}

# Daily/weekly/monthly are the well-supported intervals across both sources.
# Intraday intervals work against Yahoo only (Stooq is EOD-only and already
# raises SourceError for them, which the fallback loop handles).
SUPPORTED_INTERVALS = {"1m", "5m", "15m", "30m", "1h", "1d", "1wk", "1mo"}
# Intraday bars go stale fast; shorten the cache TTL for them.
_INTRADAY_TTL_SECONDS = 5 * 60


def _resolve_dates(
    period: str, start: Any, end: Any
) -> tuple[pd.Timestamp, pd.Timestamp]:
    end_ts = pd.Timestamp(end) if end else pd.Timestamp.today().normalize()
    if start:
        start_ts = pd.Timestamp(start)
    else:
        years = _PERIOD_YEARS.get(period, 1)
        start_ts = end_ts - pd.DateOffset(years=years)
    if start_ts >= end_ts:
        raise InvalidRequest("start must be before end")
    return start_ts, end_ts


def _covers(df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> bool:
    if df is None or df.empty:
        return False
    return bool(df.index.min() <= start and df.index.max() >= end)


def _get_one(
    ticker: str,
    start: pd.Timestamp,
    end: pd.Timestamp,
    interval: str,
    sources: list[str],
    offline: bool,
) -> pd.DataFrame:
    if interval not in SUPPORTED_INTERVALS:
        raise InvalidRequest(f"unsupported interval '{interval}'")
    ttl = _INTRADAY_TTL_SECONDS if interval not in ("1d", "1wk", "1mo") else None

    # 1) try cache
    for src in sources:
        df, fresh = cache.read(src, ticker, interval, offline=offline, ttl_seconds=ttl)
        if df is not None and fresh and _covers(df, start, end):
            return df.loc[start:end]
    if offline:
        raise DataUnavailable(f"{ticker}: no fresh cache and offline=True")

    # 2) try sources in order, fall back on failure
    errors: list[str] = []
    for src in sources:
        try:
            raw = get_source(src).fetch(ticker, start, end, interval)
            df = clean.normalize(raw, source=src)
            cache.write(src, ticker, interval, df)
            return df.loc[start:end]
        except (RateLimited, SourceError, DataUnavailable) as e:
            errors.append(f"{src}: {e}")
            continue
    raise DataUnavailable(f"{ticker}: all sources failed -> {errors}")


def _combine(frames: dict[str, pd.DataFrame], *, wide: bool) -> pd.DataFrame:
    if not frames:
        return pd.DataFrame(columns=clean.CANONICAL_COLUMNS)

    parts = []
    for ticker, df in frames.items():
        part = df.copy()
        part["ticker"] = ticker
        parts.append(part)
    long_df = pd.concat(parts).sort_index()
    long_df = long_df[["ticker"] + clean.CANONICAL_COLUMNS]

    if not wide:
        return long_df

    return long_df.pivot(columns="ticker")


def get(
    tickers: str | list[str],
    *,
    period: str = "1y",
    start: Any = None,
    end: Any = None,
    interval: str = "1d",
    sources: list[str] | None = None,
    offline: bool | None = None,
    wide: bool = False,
) -> pd.DataFrame:
    """Public entry point. Single ticker -> single frame; list -> long frame."""
    resolved_sources = sources or config.DEFAULT_SOURCE_ORDER
    resolved_offline = config.OFFLINE if offline is None else offline
    start_ts, end_ts = _resolve_dates(period, start, end)

    if isinstance(tickers, str):
        return _get_one(
            tickers.upper(), start_ts, end_ts, interval, resolved_sources, resolved_offline
        )

    symbols = [t.upper() for t in tickers]
    frames: dict[str, pd.DataFrame] = {}
    max_workers = min(8, len(symbols)) or 1
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(
                _get_one, sym, start_ts, end_ts, interval, resolved_sources, resolved_offline
            ): sym
            for sym in symbols
        }
        for future, sym in futures.items():
            try:
                frames[sym] = future.result()
            except DataUnavailable:
                continue  # skip failed tickers, don't kill the whole call
    return _combine(frames, wide=wide)


def resample(data: pd.DataFrame, interval: str) -> pd.DataFrame:
    """Resample a canonical daily OHLCV frame to a coarser interval (e.g. "1wk", "1mo").

    Aggregation follows standard OHLCV rules: open=first, high=max, low=min,
    close/adj_close=last, volume=sum.
    """
    freq = {"1wk": "W", "1mo": "M"}.get(interval)
    if freq is None:
        raise InvalidRequest(f"resample target must be '1wk' or '1mo', got '{interval}'")

    agg = {
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "adj_close": "last",
        "volume": "sum",
    }
    cols = {k: v for k, v in agg.items() if k in data.columns}
    out = data.resample(freq).agg(cols)
    return out.dropna(how="all")
