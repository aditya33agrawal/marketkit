# marketkit

[![CI](https://github.com/aditya33agrawal/marketkit/actions/workflows/ci.yml/badge.svg)](https://github.com/aditya33agrawal/marketkit/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/marketkit.svg)](https://pypi.org/project/marketkit/)
[![Python versions](https://img.shields.io/pypi/pyversions/marketkit.svg)](https://pypi.org/project/marketkit/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**Reliable, clean market data and analytics — pure Python, no C dependencies.**

`marketkit` fetches OHLCV price history from public sources, normalizes it into
one predictable `DataFrame` shape, and gives you the analytics and indicators you
need on top of it — returns, risk metrics, drawdown, and a standard set of
technical indicators — all behind a tiny, beginner-friendly API.

```python
import marketkit as mk

df = mk.get("RELIANCE.NS", period="2y")   # clean, adjusted OHLCV
mk.sharpe(df)                             # -0.12
df["rsi"] = mk.rsi(df)                    # add an indicator column
mk.summary("RELIANCE.NS")                 # one-line risk/return report
```

---

## Table of contents

- [Why marketkit](#why-marketkit)
- [Install](#install)
- [Quick start](#quick-start)
- [What you can do](#what-you-can-do)
  - [Fetching data](#1-fetching-data)
  - [The data contract](#2-the-data-contract)
  - [Returns &amp; growth](#3-returns--growth)
  - [Risk metrics](#4-risk-metrics)
  - [Technical indicators](#5-technical-indicators)
  - [One-shot summary](#6-one-shot-summary)
- [Caching &amp; offline mode](#caching--offline-mode)
- [Reliability &amp; error handling](#reliability--error-handling)
- [Configuration](#configuration)
- [Full API reference](#full-api-reference)
- [Development](#development)
- [Disclaimer](#disclaimer)

---

## Why marketkit

- **Pure Python** — installs with a plain `pip install`. No compiler, no system
  libraries, no wheels that fail on Apple Silicon or locked-down CI runners.
- **Doesn't break** — automatic source fallback (Yahoo → Stooq) plus local
  caching, so one bad day from a data provider doesn't crash your script.
- **Clean, predictable output** — flat columns, stable dtypes, adjusted prices
  by default. The same shape every time, whether you ask for one ticker or fifty.
- **Beginner-friendly** — sensible defaults, clear exceptions, a small surface
  area you can learn in five minutes.
- **Typed** — ships a `py.typed` marker and passes `mypy --strict`.

---

## Install

```bash
pip install marketkit
```

Requires **Python 3.9+**. The only runtime dependencies are `pandas`,
`requests`, `pyarrow`, and `platformdirs` — all pure-Python or pre-built wheels.

---

## Quick start

```python
import marketkit as mk

# 1. Fetch clean, adjusted OHLCV data
df = mk.get("RELIANCE.NS", period="2y")

# 2. Risk / return analytics
mk.cagr(df)        # -0.046  (compound annual growth rate)
mk.sharpe(df)      # -0.12   (annualized Sharpe ratio)
mk.drawdown(df)    # (drawdown series, max drawdown)

# 3. Indicators — return Series/DataFrames you can assign back
df["sma50"] = mk.sma(df, window=50)
df["rsi"] = mk.rsi(df)

# 4. One-shot summary, no manual fetch needed
mk.summary("RELIANCE.NS")
```

> Indian listings use Yahoo's exchange suffixes — `.NS` for NSE
> (`RELIANCE.NS`, `TCS.NS`, `INFY.NS`) and `.BO` for BSE (`RELIANCE.BO`).

A runnable, end-to-end walkthrough (with plots) lives in
[`examples/quickstart.ipynb`](examples/quickstart.ipynb).

---

## What you can do

### 1. Fetching data

`mk.get()` is the single entry point for price history. It handles single or
multiple tickers, date ranges or named periods, intervals, source selection, and
offline reads.

```python
mk.get("RELIANCE.NS")                                 # 1 year of daily bars
mk.get("RELIANCE.NS", period="5y")                     # "1y" | "2y" | "5y" | "10y" | "max"
mk.get("RELIANCE.NS", start="2020-01-01", end="2023-01-01")
mk.get("RELIANCE.NS", interval="1wk")                  # "1d" | "1wk" | "1mo"

# Multiple tickers — long (tidy) frame by default, with a `ticker` column
mk.get(["RELIANCE.NS", "TCS.NS", "INFY.NS"])

# Multiple tickers — wide frame, one column level per ticker
mk.get(["RELIANCE.NS", "TCS.NS", "INFY.NS"], wide=True)

# Choose / reorder sources, or pin a single source
mk.get("RELIANCE.NS", sources=["stooq"])

# Cache-only: never touch the network
mk.get("RELIANCE.NS", offline=True)
```

Tickers are case-insensitive (`"reliance.ns"` → `"RELIANCE.NS"`). In a multi-ticker request,
tickers that fail on every source are **silently skipped** rather than killing
the whole call — you always get back whatever succeeded.

### 2. The data contract

Every frame `marketkit` returns has the **same canonical shape**, so downstream
code never has to special-case a provider's quirks.

| Property | Guarantee |
|---|---|
| Index | `DatetimeIndex` named `date`, timezone-naive, sorted ascending, no duplicates |
| Columns | `open`, `high`, `low`, `close`, `adj_close`, `volume` (exactly, in this order) |
| OHLC / `adj_close` dtype | `float64` |
| `volume` dtype | `Int64` (pandas nullable integer) |
| Adjusted prices | `adj_close` is **always** present; equals `close` if the source has no adjusted series |
| Multi-ticker | adds a `ticker` column (long format) or one column level per ticker (`wide=True`) |

This means `df["adj_close"]`, `df["volume"]`, and a clean `date` index are always
there — no renaming, no tz wrangling, no surprise object dtypes.

### 3. Returns & growth

```python
mk.returns(df)                     # daily simple returns (Series)
mk.returns(df, kind="log")         # log returns
mk.returns(df, column="close")     # use raw close instead of adj_close

mk.cagr(df)                        # compound annual growth rate (float)
mk.cagr(df, periods_per_year=52)   # for weekly data
```

By default, returns are computed on `adj_close` so dividends and splits are
accounted for.

### 4. Risk metrics

All risk functions accept the same keyword args as `returns()` (`kind`,
`column`) plus an annualization factor, and most accept a risk-free rate.

```python
mk.volatility(df)                  # annualized standard deviation of returns
mk.sharpe(df)                      # annualized Sharpe ratio
mk.sharpe(df, rf=0.04)             # with a 4% annual risk-free rate
mk.sortino(df)                     # annualized Sortino ratio (downside risk)

dd_series, max_dd = mk.drawdown(df)  # full drawdown curve + worst drawdown
```

`drawdown()` returns a tuple: the running drawdown `Series` (peak-to-trough at
every point) and the single worst (most negative) drawdown as a float.

### 5. Technical indicators

Indicators take a price frame (or a bare `Series`) and return a `Series` or
`DataFrame` you can assign straight back onto your data. They operate on `close`
by default; pass `column="adj_close"` to use adjusted prices.

```python
mk.sma(df, window=20)              # simple moving average
mk.ema(df, window=20)              # exponential moving average
mk.rsi(df, period=14)              # Wilder's relative strength index

macd = mk.macd(df)                 # DataFrame: macd, signal, hist
macd = mk.macd(df, fast=12, slow=26, signal=9)

bands = mk.bollinger(df)           # DataFrame: mid, upper, lower
bands = mk.bollinger(df, window=20, k=2)
```

### 6. One-shot summary

When you just want the headline numbers, `summary()` fetches the data and
computes the key metrics in a single call, returning a labeled `Series`.

```python
mk.summary("RELIANCE.NS")
mk.summary("RELIANCE.NS", period="5y")
```

```text
ticker          RELIANCE.NS
start            2021-06-21
end              2026-06-19
last_close           1309.5
cagr                 0.0536
annual_vol           0.2234
sharpe                 0.35
max_drawdown        -0.2718
dtype: object
```

> Output above is the real `period="5y"` summary for `RELIANCE.NS`. Numbers
> shift as new data arrives.

---

## Caching & offline mode

Fetched data is cached locally as **Parquet** in a platform-appropriate cache
directory (resolved via `platformdirs`) and reused while still fresh — a **12h
TTL** by default for daily bars. This makes repeated runs fast and keeps you off
the network when you don't need fresh data.

```python
mk.get("RELIANCE.NS")                 # first call hits the network, caches the result
mk.get("RELIANCE.NS")                 # subsequent calls within 12h read from cache
mk.get("RELIANCE.NS", offline=True)   # force a cache-only read; raises if nothing fresh
```

You can also flip offline mode globally:

```python
import marketkit.config as config
config.OFFLINE = True          # every get() now reads cache only
```

---

## Reliability & error handling

`marketkit` tries each configured source in order and **falls back** on failure,
so a single provider outage or rate-limit doesn't break your script. When data
genuinely can't be retrieved, it raises a typed exception you can catch.

```python
from marketkit.errors import (
    MarketkitError,    # base class for everything below
    InvalidRequest,    # bad arguments (e.g. start >= end, bad interval)
    SourceError,       # a source failed in a non-recoverable way
    RateLimited,       # a source refused (HTTP 429 / auth throttling) — subclass of SourceError
    DataUnavailable,   # no source could satisfy the request
)

try:
    df = mk.get("RELIANCE.NS", period="2y")
except DataUnavailable:
    ...  # offline with no fresh cache, or every source failed
except InvalidRequest:
    ...  # you passed something invalid
```

Catching `MarketkitError` handles all of the above at once.

---

## Configuration

Defaults live in `marketkit.config` and can be overridden per-call (preferred)
or globally.

| Setting | Default | Meaning |
|---|---|---|
| `DEFAULT_SOURCE_ORDER` | `["yahoo", "stooq"]` | Source priority; first to succeed wins |
| `CACHE_TTL_SECONDS` | `43200` (12h) | How long cached bars are considered fresh |
| `CACHE_DIR` | platform cache dir | Where Parquet cache files are stored |
| `PERIODS_PER_YEAR` | `{"1d": 252, "1wk": 52, "1mo": 12}` | Annualization factors by interval |
| `REQUEST_TIMEOUT` | `15` | HTTP timeout in seconds |
| `OFFLINE` | `False` | If `True`, only read cache, never hit the network |

An optional Alpha Vantage API key is read from the `ALPHAVANTAGE_API_KEY`
environment variable (never hardcode keys).

---

## Full API reference

Everything below is importable directly from the top-level `marketkit` package.

### Data

| Function | Returns | Description |
|---|---|---|
| `get(tickers, *, period="1y", start=None, end=None, interval="1d", sources=None, offline=None, wide=False)` | `DataFrame` | Fetch clean OHLCV for one ticker or a list |

### Returns & growth

| Function | Returns | Description |
|---|---|---|
| `returns(data, *, kind="simple", column="adj_close")` | `Series` | Simple or log returns |
| `cagr(data, *, periods_per_year=252, column="adj_close")` | `float` | Compound annual growth rate |

### Risk

| Function | Returns | Description |
|---|---|---|
| `volatility(data, *, periods_per_year=252, **kw)` | `float` | Annualized volatility |
| `sharpe(data, *, rf=0.0, periods_per_year=252, **kw)` | `float` | Annualized Sharpe ratio |
| `sortino(data, *, rf=0.0, periods_per_year=252, **kw)` | `float` | Annualized Sortino ratio |
| `drawdown(data, **kw)` | `(Series, float)` | Drawdown curve and max drawdown |

### Indicators

| Function | Returns | Description |
|---|---|---|
| `sma(data, window=20, column="close")` | `Series` | Simple moving average |
| `ema(data, window=20, column="close")` | `Series` | Exponential moving average |
| `rsi(data, period=14, column="close")` | `Series` | Relative strength index (Wilder) |
| `macd(data, fast=12, slow=26, signal=9, column="close")` | `DataFrame` | MACD line, signal, histogram |
| `bollinger(data, window=20, k=2, column="close")` | `DataFrame` | Bollinger bands (mid, upper, lower) |

### Convenience

| Function | Returns | Description |
|---|---|---|
| `summary(ticker, *, period="1y", **kw)` | `Series` | Fetch + report ticker, dates, last close, CAGR, vol, Sharpe, max drawdown |

> All analytics and indicator functions accept either a canonical `DataFrame` or
> a bare price `Series`, so you can compose them however you like.

---

## Development

```bash
git clone https://github.com/aditya33agrawal/marketkit.git
cd marketkit
pip install -e ".[dev]"
pytest
```

Linting and type-checking mirror CI:

```bash
ruff check .
mypy --strict src
```

See [`docs/tech-plan.md`](docs/tech-plan.md) for the internal architecture and
the full data contract.

---

## Disclaimer

Not affiliated with any data provider. Data is for personal/research use only.
Users must comply with each source's terms of service. **This is not financial
advice.**

## License

[MIT](LICENSE) © Aditya Agrawal
