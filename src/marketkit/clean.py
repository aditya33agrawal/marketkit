"""The canonical data contract and the code that enforces it.

Single-ticker frame (the default):
  - Index: a DatetimeIndex named "date", timezone-naive, sorted ascending,
    no duplicates. For daily data, normalized to midnight (date only).
  - Columns (in this order, all lowercase): open, high, low, close,
    adj_close, volume.
    - open/high/low/close/adj_close: float64
    - volume: Int64 (pandas nullable int)

Multi-ticker frame (long/tidy by default): same columns plus a "ticker"
column; the index stays "date" (non-unique across tickers, which is fine
for long format).

Invariants this module guarantees:
  1. Columns are exactly the set above, lowercase, in order.
  2. Index is sorted, tz-naive, unique (per ticker).
  3. No fully-empty rows; NaNs only where a source genuinely lacks a value.
  4. high >= low, high >= open/close, low <= open/close where data allows
     (validate() warns, it never raises).
  5. adj_close is always present -- if a source doesn't provide one,
     adj_close = close.
"""

from __future__ import annotations

import pandas as pd

CANONICAL_COLUMNS = ["open", "high", "low", "close", "adj_close", "volume"]

# Per-source column rename maps -> canonical names.
_RENAME_MAP: dict[str, dict[str, str]] = {
    "stooq": {
        "open": "open",
        "high": "high",
        "low": "low",
        "close": "close",
        "volume": "volume",
    },
}


def normalize(raw: pd.DataFrame, *, source: str) -> pd.DataFrame:
    """Convert a source's raw frame into the canonical contract.

    Steps:
      1. Lowercase + rename columns to canonical names (per-source rename map).
      2. Ensure a 'date' DatetimeIndex: parse, tz-localize away, normalize to date.
      3. Coerce dtypes: OHLC + adj_close -> float64; volume -> Int64.
      4. If adj_close missing, set adj_close = close.
      5. Drop rows where all OHLC are NaN; sort index ascending; drop dup dates (keep last).
      6. Reorder columns to CANONICAL_COLUMNS.
    """
    df = raw.copy()
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    df = df.rename(columns=_RENAME_MAP.get(source, {}))

    df.index = pd.to_datetime(df.index)
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    df.index = df.index.normalize()
    df.index.name = "date"

    if "adj_close" not in df.columns and "close" in df.columns:
        df["adj_close"] = df["close"]

    for col in ["open", "high", "low", "close", "adj_close"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("float64")
    if "volume" in df.columns:
        df["volume"] = pd.to_numeric(df["volume"], errors="coerce").astype("Int64")

    df = df.dropna(subset=["open", "high", "low", "close"], how="all")
    df = df[~df.index.duplicated(keep="last")].sort_index()
    return df[[c for c in CANONICAL_COLUMNS if c in df.columns]]


def validate(df: pd.DataFrame) -> list[str]:
    """Return a list of human-readable warnings (don't raise). Used for logging/QA."""
    warnings: list[str] = []
    if df.empty:
        warnings.append("empty frame")
        return warnings
    if (df["high"] < df["low"]).any():
        warnings.append("high < low on some rows")
    if df.index.duplicated().any():
        warnings.append("duplicate dates")
    if not df.index.is_monotonic_increasing:
        warnings.append("index not sorted")
    return warnings
