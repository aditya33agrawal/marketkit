from __future__ import annotations

import time
from pathlib import Path

import pandas as pd

from marketkit.config import CACHE_DIR, CACHE_TTL_SECONDS


def _path(source: str, ticker: str, interval: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    safe = ticker.upper().replace("/", "_")
    return CACHE_DIR / f"{source}__{safe}__{interval}.parquet"


def read(
    source: str, ticker: str, interval: str, *, offline: bool = False
) -> tuple[pd.DataFrame | None, bool]:
    """Return (df, is_fresh) or (None, False) if no cache."""
    p = _path(source, ticker, interval)
    if not p.exists():
        return None, False
    df = pd.read_parquet(p)
    age = time.time() - p.stat().st_mtime
    is_fresh = offline or age < CACHE_TTL_SECONDS
    return df, is_fresh


def write(source: str, ticker: str, interval: str, df: pd.DataFrame) -> None:
    p = _path(source, ticker, interval)
    if p.exists():  # merge with existing range
        old = pd.read_parquet(p)
        df = pd.concat([old, df])
        df = df[~df.index.duplicated(keep="last")].sort_index()
    df.to_parquet(p)


def clear(ticker: str | None = None) -> None:
    """Wipe whole cache or just one ticker's files (for the gotchas docs)."""
    for f in CACHE_DIR.glob("*.parquet"):
        if ticker is None or f"__{ticker.upper()}__" in f.name:
            f.unlink()
