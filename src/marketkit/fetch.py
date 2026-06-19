from __future__ import annotations

from typing import Any

import pandas as pd

from marketkit import cache, clean, config
from marketkit import sources as _sources  # noqa: F401  (registers built-in sources)
from marketkit.errors import DataUnavailable, InvalidRequest, RateLimited, SourceError
from marketkit.sources.base import get_source

_PERIOD_YEARS = {"1y": 1, "2y": 2, "5y": 5, "10y": 10, "max": 50}


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
    # 1) try cache
    for src in sources:
        df, fresh = cache.read(src, ticker, interval, offline=offline)
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

    frames: dict[str, pd.DataFrame] = {}
    for t in tickers:
        try:
            frames[t.upper()] = _get_one(
                t.upper(), start_ts, end_ts, interval, resolved_sources, resolved_offline
            )
        except DataUnavailable:
            continue  # skip failed tickers, don't kill the whole call
    return _combine(frames, wide=wide)
