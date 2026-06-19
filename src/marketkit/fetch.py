from __future__ import annotations

import pandas as pd

from marketkit import cache, clean, config
from marketkit import sources as _sources  # noqa: F401  (registers built-in sources)
from marketkit.errors import DataUnavailable, InvalidRequest, RateLimited, SourceError
from marketkit.sources.base import get_source

_PERIOD_YEARS = {"1y": 1, "2y": 2, "5y": 5, "10y": 10, "max": 50}


def _resolve_dates(period, start, end):
    end = pd.Timestamp(end) if end else pd.Timestamp.today().normalize()
    if start:
        start = pd.Timestamp(start)
    else:
        years = _PERIOD_YEARS.get(period, 1)
        start = end - pd.DateOffset(years=years)
    if start >= end:
        raise InvalidRequest("start must be before end")
    return start, end


def _covers(df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> bool:
    if df is None or df.empty:
        return False
    return bool(df.index.min() <= start and df.index.max() >= end)


def _get_one(ticker, start, end, interval, sources, offline):
    # 1) try cache
    for src in sources:
        df, fresh = cache.read(src, ticker, interval, offline=offline)
        if df is not None and fresh and _covers(df, start, end):
            return df.loc[start:end]
    if offline:
        raise DataUnavailable(f"{ticker}: no fresh cache and offline=True")

    # 2) try sources in order, fall back on failure
    errors = []
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
    tickers,
    *,
    period="1y",
    start=None,
    end=None,
    interval="1d",
    sources=None,
    offline=None,
    wide=False,
):
    """Public entry point. Single ticker -> single frame; list -> long frame."""
    sources = sources or config.DEFAULT_SOURCE_ORDER
    offline = config.OFFLINE if offline is None else offline
    start, end = _resolve_dates(period, start, end)

    if isinstance(tickers, str):
        return _get_one(tickers.upper(), start, end, interval, sources, offline)

    frames = {}
    for t in tickers:
        try:
            frames[t.upper()] = _get_one(t.upper(), start, end, interval, sources, offline)
        except DataUnavailable:
            continue  # skip failed tickers, don't kill the whole call
    return _combine(frames, wide=wide)
