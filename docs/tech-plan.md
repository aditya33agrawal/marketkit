# marketkit — Technical Implementation Plan

This is the engineering blueprint: what each module does, the exact data contract they share, reference implementations for the tricky parts, and the order to build them in. Build bottom-up so every module only depends on ones already finished.

---

## 0. The keystone: the canonical data contract

**Everything in the package depends on one agreed-upon DataFrame shape.** Sources produce messy data in different formats; the clean layer converts all of it into *this* exact shape; analytics assume *this* shape. Define it once, enforce it everywhere.

**Single-ticker frame (the default):**
- **Index:** a `DatetimeIndex` named `date`, timezone-naive, sorted ascending, no duplicates. For daily data, normalized to midnight (date only).
- **Columns (in this order, all lowercase):**
  | column | dtype | notes |
  |---|---|---|
  | `open` | float64 | |
  | `high` | float64 | |
  | `low` | float64 | |
  | `close` | float64 | raw close |
  | `adj_close` | float64 | split/dividend-adjusted close |
  | `volume` | Int64 (nullable) | use pandas nullable int |

**Multi-ticker frame (long/tidy by default):** same columns plus a `ticker` column; index stays `date` (so the index is non-unique across tickers — that's fine for long format). Offer `wide=True` to pivot into a column-MultiIndex if a power user wants it.

**Invariants the clean layer guarantees:**
1. Columns are exactly the set above, lowercase, in order.
2. Index is sorted, tz-naive, unique (per ticker).
3. No fully-empty rows; `NaN`s only where a source genuinely lacks a value.
4. `high >= low`, `high >= open/close`, `low <= open/close` where data allows (validation can warn, not crash).
5. `adj_close` is always present — if a source doesn't provide one, set `adj_close = close`.

Write this contract into a docstring in `clean.py` and reference it everywhere.

---

## 1. Build order (dependency-driven)

```
errors.py          ─┐  (no deps)
config.py          ─┤  (no deps)
clean.py           ─┤  (depends on: errors)  ← defines + enforces the contract
sources/base.py    ─┤  (depends on: errors)
sources/yahoo.py   ─┤  (depends on: base, clean)
sources/stooq.py   ─┤  (depends on: base, clean)
cache.py           ─┤  (depends on: config)
fetch.py           ─┤  (depends on: sources, cache, clean, errors, config)
analytics/returns  ─┤  (depends on: contract only)
analytics/risk     ─┤  (depends on: returns)
analytics/indicators─┤ (depends on: contract only)
summary.py         ─┘  (depends on: fetch + analytics)
__init__.py            (re-exports public API)
```

Build and test each before moving up. Analytics modules are independent of the data layer — you can build and test them in parallel against synthetic data.

---

## 2. `errors.py` — exception hierarchy

A small, clear hierarchy so users (and the fallback loop) can catch the right thing.

```python
class MarketkitError(Exception):
    """Base for all marketkit errors."""

class SourceError(MarketkitError):
    """A data source failed in a non-recoverable way (bad response, parse error)."""

class RateLimited(SourceError):
    """A source refused due to rate limiting (HTTP 429) or auth throttling (401)."""

class DataUnavailable(MarketkitError):
    """No source could provide data for this request."""

class InvalidRequest(MarketkitError):
    """The caller passed bad arguments (bad ticker, bad date range, bad interval)."""
```

Rule: sources raise `RateLimited` / `SourceError`; the fetch engine catches those and falls back; if *all* sources fail it raises `DataUnavailable`. Caller-input problems raise `InvalidRequest` immediately (no fallback).

---

## 3. `config.py` — settings & defaults

Centralize every tunable so there are no magic constants scattered around.

```python
from pathlib import Path
import os
import platformdirs

# Where cached parquet files live (cross-platform)
CACHE_DIR = Path(platformdirs.user_cache_dir("marketkit"))

# Source priority order (first that succeeds wins)
DEFAULT_SOURCE_ORDER = ["yahoo", "stooq"]

# Cache freshness: daily bars considered stale after this many seconds
CACHE_TTL_SECONDS = 60 * 60 * 12   # 12h

# Trading periods per year, by interval (for annualizing)
PERIODS_PER_YEAR = {"1d": 252, "1wk": 52, "1mo": 12}

# HTTP
REQUEST_TIMEOUT = 15
USER_AGENT = "marketkit/0.1 (+https://github.com/YOUR_USERNAME/marketkit)"

# Optional API keys read from environment (never hardcode)
def alpha_vantage_key() -> str | None:
    return os.environ.get("ALPHAVANTAGE_API_KEY")

# Global toggles (can be overridden at call time)
OFFLINE = False   # if True, only read cache, never hit network
```

Expose a tiny settings object or just import these constants. Keep it boring.

---

## 4. `clean.py` — normalization & validation (the contract enforcer)

This is the most important non-trivial module. Every source's raw output passes through `normalize()`.

```python
import pandas as pd

CANONICAL_COLUMNS = ["open", "high", "low", "close", "adj_close", "volume"]

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
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    df = df.rename(columns=_RENAME_MAP.get(source, {}))

    # index -> tz-naive DatetimeIndex named 'date'
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
    warnings = []
    if df.empty:
        warnings.append("empty frame")
    if (df["high"] < df["low"]).any():
        warnings.append("high < low on some rows")
    if df.index.duplicated().any():
        warnings.append("duplicate dates")
    if not df.index.is_monotonic_increasing:
        warnings.append("index not sorted")
    return warnings
```

`_RENAME_MAP` is a per-source dict, e.g. Stooq's `Open/High/Low/Close/Volume` → canonical. Keep each source's quirks isolated here.

---

## 5. `sources/base.py` — the source contract + registry

Every source implements the same tiny interface and registers itself.

```python
from typing import Protocol, runtime_checkable
import pandas as pd

@runtime_checkable
class Source(Protocol):
    name: str
    requires_key: bool

    def fetch(self, ticker: str, start, end, interval: str) -> pd.DataFrame:
        """Return a RAW frame (any shape). The engine will normalize it.
        Raise RateLimited / SourceError on failure."""
        ...

_REGISTRY: dict[str, Source] = {}

def register(source: Source) -> None:
    _REGISTRY[source.name] = source

def get_source(name: str) -> Source:
    return _REGISTRY[name]
```

Sources call `register(...)` at import time. The fetch engine looks them up by name from `DEFAULT_SOURCE_ORDER`.

---

## 6. `sources/yahoo.py` — primary source

Uses Yahoo's undocumented chart JSON endpoint (the same one yfinance uses). **It's unofficial and can change/throttle — that's exactly why fallback + caching exist.** Send a User-Agent, handle 401/429 as `RateLimited`.

```python
import requests, pandas as pd
from datetime import datetime
from marketkit.config import REQUEST_TIMEOUT, USER_AGENT
from marketkit.errors import RateLimited, SourceError
from marketkit.sources.base import register

_BASE = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"

class YahooSource:
    name = "yahoo"
    requires_key = False

    def fetch(self, ticker, start, end, interval):
        params = {
            "period1": int(pd.Timestamp(start).timestamp()),
            "period2": int(pd.Timestamp(end).timestamp()),
            "interval": interval,
            "events": "div,splits",
            "includeAdjustedClose": "true",
        }
        try:
            r = requests.get(_BASE.format(ticker=ticker), params=params,
                             headers={"User-Agent": USER_AGENT},
                             timeout=REQUEST_TIMEOUT)
        except requests.RequestException as e:
            raise SourceError(f"yahoo network error: {e}") from e

        if r.status_code in (401, 429):
            raise RateLimited(f"yahoo throttled (HTTP {r.status_code})")
        if r.status_code != 200:
            raise SourceError(f"yahoo HTTP {r.status_code}")

        result = r.json()["chart"]["result"]
        if not result:
            raise SourceError("yahoo returned no result")
        res = result[0]
        ts = res["timestamp"]
        q = res["indicators"]["quote"][0]
        adj = res["indicators"].get("adjclose", [{}])[0].get("adjclose")

        df = pd.DataFrame({
            "open": q["open"], "high": q["high"], "low": q["low"],
            "close": q["close"], "volume": q["volume"],
            "adj_close": adj if adj is not None else q["close"],
        }, index=pd.to_datetime(ts, unit="s"))
        return df  # raw; engine normalizes

register(YahooSource())
```

Edge cases to handle later: missing keys in `quote`, `null` values mid-series (normalize coerces them to NaN), invalid ticker (Yahoo returns an error payload → raise `SourceError`).

---

## 7. `sources/stooq.py` — fallback source (EOD only)

Stooq serves CSV. US tickers usually need a `.us` suffix. Daily data only — if an intraday interval is requested, raise `SourceError` so the engine moves on (or skips Stooq).

```python
import requests, io, pandas as pd
from marketkit.config import REQUEST_TIMEOUT, USER_AGENT
from marketkit.errors import SourceError
from marketkit.sources.base import register

_URL = "https://stooq.com/q/d/l/"

class StooqSource:
    name = "stooq"
    requires_key = False

    def fetch(self, ticker, start, end, interval):
        if interval != "1d":
            raise SourceError("stooq supports daily only")
        symbol = ticker.lower()
        if "." not in symbol:
            symbol += ".us"
        params = {"s": symbol, "i": "d",
                  "d1": pd.Timestamp(start).strftime("%Y%m%d"),
                  "d2": pd.Timestamp(end).strftime("%Y%m%d")}
        r = requests.get(_URL, params=params,
                         headers={"User-Agent": USER_AGENT},
                         timeout=REQUEST_TIMEOUT)
        if r.status_code != 200 or r.text.strip().startswith("<"):
            raise SourceError(f"stooq failed (HTTP {r.status_code})")
        df = pd.read_csv(io.StringIO(r.text))
        if df.empty or "Date" not in df.columns:
            raise SourceError("stooq returned no usable data")
        df = df.set_index("Date")   # columns: Open/High/Low/Close/Volume
        return df  # raw; clean._RENAME_MAP['stooq'] maps to canonical

register(StooqSource())
```

---

## 8. `cache.py` — persistent Parquet cache + offline mode

Goal: avoid refetching, survive source outages, enable reproducible offline runs.

**Key scheme:** one parquet file per `(source, ticker, interval)` storing the **widest range fetched so far**. On a request, if the cache covers the requested range and is fresh, slice and return; otherwise fetch, merge, rewrite.

**Staleness:** file modified-time + `CACHE_TTL_SECONDS`. In offline mode, ignore staleness and return whatever exists.

```python
import time, pandas as pd
from pathlib import Path
from marketkit.config import CACHE_DIR, CACHE_TTL_SECONDS

def _path(source, ticker, interval) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    safe = ticker.upper().replace("/", "_")
    return CACHE_DIR / f"{source}__{safe}__{interval}.parquet"

def read(source, ticker, interval, *, offline=False):
    """Return (df, is_fresh) or (None, False) if no cache."""
    p = _path(source, ticker, interval)
    if not p.exists():
        return None, False
    df = pd.read_parquet(p)
    age = time.time() - p.stat().st_mtime
    is_fresh = offline or age < CACHE_TTL_SECONDS
    return df, is_fresh

def write(source, ticker, interval, df: pd.DataFrame) -> None:
    p = _path(source, ticker, interval)
    if p.exists():                      # merge with existing range
        old = pd.read_parquet(p)
        df = pd.concat([old, df])
        df = df[~df.index.duplicated(keep="last")].sort_index()
    df.to_parquet(p)

def clear(ticker=None) -> None:
    """Wipe whole cache or just one ticker's files (for the gotchas docs)."""
    for f in CACHE_DIR.glob("*.parquet"):
        if ticker is None or f"__{ticker.upper()}__" in f.name:
            f.unlink()
```

Document the cache location and `clear()` in the gotchas page — "why am I getting stale data" is a top beginner question.

---

## 9. `fetch.py` — the orchestration engine (the heart)

Ties cache + sources + clean together with the fallback algorithm.

```python
import pandas as pd
from datetime import datetime, timedelta
from marketkit import cache, clean, config
from marketkit.errors import DataUnavailable, InvalidRequest, RateLimited, SourceError
from marketkit.sources.base import get_source

def _resolve_dates(period, start, end):
    end = pd.Timestamp(end) if end else pd.Timestamp.today().normalize()
    if start:
        start = pd.Timestamp(start)
    else:
        years = {"1y": 1, "2y": 2, "5y": 5, "10y": 10, "max": 50}.get(period, 1)
        start = end - pd.DateOffset(years=years)
    if start >= end:
        raise InvalidRequest("start must be before end")
    return start, end

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

def get(tickers, *, period="1y", start=None, end=None, interval="1d",
        sources=None, offline=None, wide=False):
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
```

`_covers(df, start, end)` checks the cached index spans the request; `_combine` builds the long (or wide) multi-ticker frame. Multi-ticker fetch is sequential in the MVP; async is a Stage-2 upgrade.

---

## 10. `analytics/returns.py`

```python
import numpy as np, pandas as pd

def returns(data, *, kind="simple", column="adj_close"):
    px = data[column] if isinstance(data, pd.DataFrame) else data
    if kind == "log":
        return np.log(px / px.shift(1)).dropna()
    return px.pct_change().dropna()

def cagr(data, *, periods_per_year=252, column="adj_close"):
    px = data[column] if isinstance(data, pd.DataFrame) else data
    total = px.iloc[-1] / px.iloc[0]
    years = len(px) / periods_per_year
    return total ** (1 / years) - 1
```

---

## 11. `analytics/risk.py`

Get the annualization and risk-free conversion right — these are the classic silent bugs.

```python
import numpy as np
from marketkit.analytics.returns import returns

def volatility(data, *, periods_per_year=252, **kw):
    r = returns(data, **kw)
    return r.std(ddof=1) * np.sqrt(periods_per_year)

def sharpe(data, *, rf=0.0, periods_per_year=252, **kw):
    r = returns(data, **kw)
    rf_per = (1 + rf) ** (1 / periods_per_year) - 1   # annual rf -> per-period
    excess = r - rf_per
    return (excess.mean() / r.std(ddof=1)) * np.sqrt(periods_per_year)

def sortino(data, *, rf=0.0, periods_per_year=252, **kw):
    r = returns(data, **kw)
    rf_per = (1 + rf) ** (1 / periods_per_year) - 1
    excess = r - rf_per
    downside = excess[excess < 0].std(ddof=1)
    return (excess.mean() / downside) * np.sqrt(periods_per_year)

def drawdown(data, **kw):
    """Return (drawdown_series, max_drawdown)."""
    r = returns(data, **kw)
    curve = (1 + r).cumprod()
    peak = curve.cummax()
    dd = curve / peak - 1
    return dd, dd.min()
```

---

## 12. `analytics/indicators.py`

Pure pandas/numpy — no ta-lib. RSI is the one people get wrong; use Wilder's smoothing (`ewm(alpha=1/period)`).

```python
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
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()   # Wilder
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
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
    return pd.DataFrame({"mid": mid, "upper": mid + k*std, "lower": mid - k*std})
```

---

## 13. `summary.py` — the beginner hook

One call that fetches and prints/returns the headline stats.

```python
import pandas as pd
from marketkit.fetch import get
from marketkit.analytics.returns import cagr
from marketkit.analytics.risk import volatility, sharpe, drawdown

def summary(ticker, *, period="1y", **kw):
    df = get(ticker, period=period, **kw)
    _, max_dd = drawdown(df)
    return pd.Series({
        "ticker": ticker.upper(),
        "start": df.index[0].date(),
        "end": df.index[-1].date(),
        "last_close": round(df["close"].iloc[-1], 2),
        "cagr": round(cagr(df), 4),
        "annual_vol": round(volatility(df), 4),
        "sharpe": round(sharpe(df), 2),
        "max_drawdown": round(max_dd, 4),
    })
```

---

## 14. `__init__.py` — public surface

```python
from marketkit._version import __version__
from marketkit.fetch import get
from marketkit.summary import summary
from marketkit.analytics.returns import returns, cagr
from marketkit.analytics.risk import volatility, sharpe, sortino, drawdown
from marketkit.analytics.indicators import sma, ema, rsi, macd, bollinger

__all__ = ["__version__", "get", "summary", "returns", "cagr",
           "volatility", "sharpe", "sortino", "drawdown",
           "sma", "ema", "rsi", "macd", "bollinger"]
```

---

## 15. Testing plan (per module, all offline)

CI must never hit live APIs. Record one real response per source into `tests/fixtures/`, replay with `responses`.

- **`test_clean.py`** — feed a messy raw frame (mixed-case cols, tz-aware index, dup dates, missing adj_close), assert the output matches the contract exactly (column names/order/dtypes, sorted unique index, `adj_close==close` fallback).
- **`test_analytics.py`** — hand-compute on a tiny series (e.g. closes `[100, 110, 105, 120]`) and assert `returns`, `cagr`, `volatility`, `drawdown`, `rsi`, `sma`, `ema`, `macd` match expected values to a tolerance. **This is where correctness bugs hide — be thorough.**
- **`test_cache.py`** — write then read returns identical data; second read flagged fresh; after monkeypatching mtime older than TTL, flagged stale; `offline=True` returns stale data without a network call.
- **`test_fetch.py`** — mock source #1 raising `RateLimited`, assert source #2 is used (fallback works); mock all sources failing, assert `DataUnavailable`; cached fresh data returns without calling any source (patch sources to raise if called).

Target >85% coverage. Use a `conftest.py` that points `CACHE_DIR` at a `tmp_path` so tests never touch the real cache.

---

## 16. Edge cases to handle before 1.0

- Invalid/delisted ticker → all sources fail cleanly → `DataUnavailable`, not a crash.
- `NaN` runs mid-series (Yahoo nulls) → coerced in clean, analytics use `.dropna()` where needed.
- Requested range partly in the future / weekend → just return what exists.
- Very short series (< indicator window) → indicators return `NaN` head, not an error.
- Multi-ticker where some succeed and some fail → return the successes, skip the rest.
- Stooq intraday request → skip Stooq, don't fail the whole call.
- Timezone consistency → everything tz-naive after clean; document that daily timestamps are calendar dates.

---

## 17. Build checklist (do in this order)

1. `errors.py` + `config.py` (trivial, no tests needed beyond import).
2. `clean.py` + `test_clean.py` — lock the contract first.
3. `analytics/` (returns → risk → indicators) + `test_analytics.py` — fully testable with synthetic data, no network.
4. `sources/base.py`, then `yahoo.py` and `stooq.py` (record fixtures while writing them).
5. `cache.py` + `test_cache.py`.
6. `fetch.py` + `test_fetch.py` — wires it all together; this is where the package "comes alive."
7. `summary.py`, `__init__.py`.
8. README quickstart that actually runs end to end.
9. Bump `_version.py` to `0.1.0`, tag `v0.1.0`, let CI publish.

Ship 0.1.0 the moment steps 1–8 pass. Resist adding more sources/indicators until real users tell you what they need.
