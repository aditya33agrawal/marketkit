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
  - [Statistics (beta, correlation, regime tools)](#6-statistics)
  - [Plotting](#7-plotting)
  - [Signals](#8-signals)
  - [One-shot summary &amp; reports](#9-one-shot-summary--reports)
  - [Ergonomics: `.mk` accessor, `Ticker`, `compare`/`screen`](#10-ergonomics)
  - [Command-line interface](#11-command-line-interface)
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

Plotting and a couple of statistical helpers are optional extras so the base
install never pulls in matplotlib/plotly/scipy:

```bash
pip install marketkit[plot]      # matplotlib charts
pip install marketkit[plotly]    # interactive plotly charts
pip install marketkit[stats]     # scipy, for select statistical helpers
pip install marketkit[all]       # everything above
```

Calling a plotting function without the extra installed raises
`marketkit.errors.PlottingUnavailable` with the exact `pip install` command
to run — it never fails with a bare `ImportError`.

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
mk.get("RELIANCE.NS", interval="5m")                   # intraday: "1m"|"5m"|"15m"|"30m"|"1h" too

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
tickers are fetched concurrently and tickers that fail on every source are
**silently skipped** rather than killing the whole call — you always get back
whatever succeeded.

Intraday bars (`1m`/`5m`/`15m`/`30m`/`1h`) use a shorter 5-minute cache TTL
instead of the daily 12h TTL, since they go stale much faster. Use
`resample()` to roll daily bars up to weekly/monthly:

```python
weekly = mk.resample(df, "1wk")
monthly = mk.resample(df, "1mo")
```

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

### 6. Statistics

Beyond risk metrics, `marketkit` ships a set of statistical tools for
comparing a ticker against a benchmark or studying its own return behavior.

```python
mk.beta(df, benchmark_df)                  # market beta
mk.alpha(df, benchmark_df, rf=0.04)        # Jensen's alpha
mk.correlation(df, benchmark_df)           # return correlation
mk.tracking_error(df, benchmark_df)        # annualized std of return spread
mk.information_ratio(df, benchmark_df)     # active return / tracking error
mk.rolling_beta(df, benchmark_df, window=63)

mk.zscore(df, window=20)                   # rolling or full-sample z-score
mk.normalize(df, base=100)                 # rebase a price series to 100
mk.autocorr(df, lags=10)                   # return autocorrelation by lag
mk.linreg_channel(df, window=20, k=2)      # rolling OLS trend channel
mk.hurst(df)                               # Hurst exponent (trend vs. mean-reversion)
mk.rolling_corr({"a": df_a, "b": df_b}, window=30)  # pairwise rolling correlation
```

Calmar, Omega, VaR/CVaR, downside deviation, the Ulcer index, and rolling
Sharpe/volatility live alongside the original risk metrics:

```python
mk.calmar(df)               # CAGR / |max drawdown|
mk.omega(df, threshold=0.0)
mk.var(df, level=0.05)                       # historical VaR (default)
mk.var(df, level=0.05, method="gaussian")    # parametric VaR
mk.cvar(df, level=0.05)                      # expected shortfall beyond VaR
mk.downside_deviation(df)
mk.ulcer_index(df)
mk.rolling_sharpe(df, window=63)
mk.rolling_volatility(df, window=63)
```

### 7. Plotting

`marketkit[plot]` (or `[plotly]`) adds chart functions that take the same
canonical `DataFrame` you already have — no separate plotting data prep.

```python
mk.plot(df, column="close")                          # line chart
mk.plot(df, kind="candle")                            # candlesticks
mk.plot(df, indicators=["sma:50", "ema:20"])           # overlay indicators on price
mk.plot_indicators(df, ["sma:50", "rsi", "macd"])      # overlays + stacked sub-panels
mk.candlestick(df, volume=True)                        # candles with a volume sub-axis
mk.plot_drawdown(df)                                   # drawdown curve
mk.plot_returns(df, kind="hist")                        # return distribution
mk.plot_returns(df, kind="cumulative")                  # cumulative growth curve
mk.plot_correlation({"RELIANCE": df_a, "TCS": df_b})   # correlation heatmap

# Multi-ticker (long-format) frames can be rebased to a common start
mk.plot(long_df, column="close", rebase=True)

# Interactive charts via Plotly instead of matplotlib
mk.plot(df, kind="candle", backend="plotly")
```

Indicator overlays are specified as strings (`"sma:50"`, `"macd:12,26,9"`);
`plot_indicators()` decides whether each one draws on the price axis
(SMA/EMA/Bollinger/...) or its own stacked panel (RSI/MACD/ADX/...).

### 8. Signals

Boolean helper functions for spotting common crossover patterns — these are
building blocks, **not a backtester**: no position sizing, no P&amp;L, no
execution modeling.

```python
mk.crossover(fast_series, slow_series)     # True where fast crosses above slow
mk.crossunder(fast_series, slow_series)    # True where fast crosses below slow
mk.golden_cross(df, fast=50, slow=200)     # SMA50 crossing above SMA200
mk.death_cross(df, fast=50, slow=200)      # SMA50 crossing below SMA200
mk.rsi_oversold(df, threshold=30)
mk.rsi_overbought(df, threshold=70)
```

### 9. One-shot summary & reports

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

For a fuller picture, `report()` (requires `marketkit[plot]`) builds a 4-panel
tear sheet — price with SMA20/SMA50, drawdown, return histogram, rolling
63-day Sharpe — and returns the same metrics alongside the figure:

```python
fig, metrics = mk.report("RELIANCE.NS", period="2y")
fig.savefig("reliance_report.png")
```

### 10. Ergonomics

A pandas accessor, a stateful `Ticker` object, and multi-ticker screening
helpers cut down on repeated `get()` calls when you're working with the same
frame or symbol set repeatedly.

```python
# .mk accessor — works on any canonical marketkit DataFrame
df = mk.get("RELIANCE.NS")
df.mk.sharpe()
df.mk.rsi()
df.mk.plot(indicators=["sma:50"])

# Ticker — fetches once, exposes everything as a method
t = mk.Ticker("RELIANCE.NS", period="2y")
t.sharpe()
t.rsi()
t.plot()

# compare() — a metrics table across several tickers
mk.compare(["RELIANCE.NS", "TCS.NS", "INFY.NS"], metrics=["cagr", "sharpe", "max_drawdown"])

# screen() — filter tickers by a predicate over their metrics
mk.screen(["RELIANCE.NS", "TCS.NS", "INFY.NS"], filters={"sharpe": lambda s: s > 0.5})
```

### 11. Command-line interface

Installing `marketkit` also installs a `marketkit` console script for quick
terminal use:

```bash
marketkit get RELIANCE.NS --period 5y --out reliance.csv
marketkit summary RELIANCE.NS
marketkit plot RELIANCE.NS --indicators sma:50,rsi --save chart.png   # needs marketkit[plot]
```

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
    MarketkitError,             # base class for everything below
    InvalidRequest,             # bad arguments (e.g. start >= end, bad interval)
    SourceError,                # a source failed in a non-recoverable way
    RateLimited,                # a source refused (HTTP 429 / auth throttling) — subclass of SourceError
    DataUnavailable,            # no source could satisfy the request
    PlottingUnavailable,        # matplotlib isn't installed — run `pip install marketkit[plot]`
    OptionalDependencyMissing,  # some other optional extra is missing
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
| `get(tickers, *, period="1y", start=None, end=None, interval="1d", sources=None, offline=None, wide=False)` | `DataFrame` | Fetch clean OHLCV for one ticker or a list. Multi-ticker requests fetch concurrently |
| `resample(data, interval)` | `DataFrame` | Roll daily OHLCV up to `"1wk"` or `"1mo"` bars |

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
| `calmar(data, *, periods_per_year=252, **kw)` | `float` | CAGR / \|max drawdown\| (`±inf`/`nan` if no drawdown) |
| `omega(data, *, threshold=0.0, **kw)` | `float` | Omega ratio around a return threshold |
| `var(data, *, level=0.05, method="historical", **kw)` | `float` | Value at Risk (`"historical"` or `"gaussian"`) |
| `cvar(data, *, level=0.05, **kw)` | `float` | Conditional VaR / expected shortfall |
| `downside_deviation(data, *, threshold=0.0, **kw)` | `float` | Std. dev. of below-threshold returns |
| `ulcer_index(data, **kw)` | `float` | RMS of drawdown depth |
| `rolling_sharpe(data, *, window=63, **kw)` | `Series` | Rolling annualized Sharpe |
| `rolling_volatility(data, *, window=63, **kw)` | `Series` | Rolling annualized volatility |

### Indicators

| Function | Returns | Description |
|---|---|---|
| `sma(data, window=20, column="close")` | `Series` | Simple moving average |
| `ema(data, window=20, column="close")` | `Series` | Exponential moving average |
| `wma(data, window=20, column="close")` | `Series` | Weighted moving average |
| `hma(data, window=20, column="close")` | `Series` | Hull moving average |
| `dema(data, window=20, column="close")` | `Series` | Double exponential moving average |
| `tema(data, window=20, column="close")` | `Series` | Triple exponential moving average |
| `rsi(data, period=14, column="close")` | `Series` | Relative strength index (Wilder) |
| `macd(data, fast=12, slow=26, signal=9, column="close")` | `DataFrame` | MACD line, signal, histogram |
| `bollinger(data, window=20, k=2, column="close")` | `DataFrame` | Bollinger bands (mid, upper, lower) |
| `true_range(data)` | `Series` | True range (needs OHLC) |
| `atr(data, period=14)` | `Series` | Average true range, Wilder-smoothed |
| `stochastic(data, k=14, d=3)` | `DataFrame` | Stochastic oscillator (`%K`, `%D`) |
| `williams_r(data, period=14)` | `Series` | Williams %R |
| `cci(data, period=20)` | `Series` | Commodity channel index |
| `adx(data, period=14)` | `DataFrame` | Average directional index (`adx`, `+di`, `-di`), Wilder-smoothed |
| `roc(data, period=12, column="close")` | `Series` | Rate of change (%) |
| `momentum(data, period=12, column="close")` | `Series` | Raw price momentum |
| `obv(data)` | `Series` | On-balance volume |
| `vwap(data)` | `Series` | Volume-weighted average price (cumulative) |
| `mfi(data, period=14)` | `Series` | Money flow index |
| `keltner(data, window=20, k=2, column="close")` | `DataFrame` | Keltner channel (mid, upper, lower) |
| `donchian(data, window=20)` | `DataFrame` | Donchian channel (upper, mid, lower) |
| `ichimoku(data, *, tenkan=9, kijun=26, senkou_b=52)` | `DataFrame` | Ichimoku cloud components |
| `psar(data, step=0.02, max_step=0.2)` | `Series` | Parabolic SAR |

### Statistics

| Function | Returns | Description |
|---|---|---|
| `beta(data, benchmark, **kw)` | `float` | Market beta vs. a benchmark |
| `alpha(data, benchmark, *, rf=0.0, **kw)` | `float` | Jensen's alpha vs. a benchmark |
| `correlation(data, benchmark, **kw)` | `float` | Return correlation |
| `tracking_error(data, benchmark, **kw)` | `float` | Annualized std. dev. of return spread |
| `information_ratio(data, benchmark, **kw)` | `float` | Active return / tracking error |
| `rolling_beta(data, benchmark, *, window=63, **kw)` | `Series` | Rolling beta |
| `zscore(data, *, window=None, column="close")` | `Series` | Rolling or full-sample z-score |
| `normalize(data, *, base=100, column="close")` | `Series` | Rebase a price series to a common start |
| `autocorr(data, *, lags=20, **kw)` | `Series` | Return autocorrelation by lag |
| `linreg_channel(data, *, window=100, k=2.0, column="close")` | `DataFrame` | Rolling OLS trend channel (mid, upper, lower) |
| `hurst(data, *, max_lag=100, column="close")` | `float` | Hurst exponent |
| `rolling_corr(series_map, *, window=30)` | `DataFrame` | Pairwise rolling correlation, tuple-keyed columns |

### Plotting (`marketkit[plot]` / `[plotly]`)

| Function | Returns | Description |
|---|---|---|
| `plot(data, *, kind="line", column="adj_close", indicators=None, ax=None, rebase=False, backend="matplotlib")` | `Axes` (or Plotly `Figure`) | Line or candlestick chart with optional overlays |
| `candlestick(data, *, volume=False, ax=None)` | `Axes` | Candlestick chart, optional volume sub-axis |
| `plot_indicators(data, indicators, *, ax=None)` | `Axes` or `list[Axes]` | Overlays + stacked panel indicators |
| `plot_drawdown(data, **kw)` | `Axes` | Drawdown curve |
| `plot_returns(data, *, kind="hist", **kw)` | `Axes` | Return histogram (`"hist"`) or cumulative growth (`"cumulative"`) |
| `plot_correlation(series_map, **kw)` | `Axes` | Correlation heatmap across tickers |

### Signals

| Function | Returns | Description |
|---|---|---|
| `crossover(fast, slow)` | `Series[bool]` | `True` where `fast` crosses above `slow` |
| `crossunder(fast, slow)` | `Series[bool]` | `True` where `fast` crosses below `slow` |
| `golden_cross(data, *, fast=50, slow=200)` | `Series[bool]` | SMA(`fast`) crossing above SMA(`slow`) |
| `death_cross(data, *, fast=50, slow=200)` | `Series[bool]` | SMA(`fast`) crossing below SMA(`slow`) |
| `rsi_oversold(data, *, period=14, threshold=30, column="close")` | `Series[bool]` | RSI below `threshold` |
| `rsi_overbought(data, *, period=14, threshold=70, column="close")` | `Series[bool]` | RSI above `threshold` |

### Convenience

| Function | Returns | Description |
|---|---|---|
| `summary(ticker, *, period="1y", **kw)` | `Series` | Fetch + report ticker, dates, last close, CAGR, vol, Sharpe, max drawdown |
| `report(ticker, *, period="1y", **kw)` | `(Figure, Series)` | 4-panel tear sheet + the same headline metrics (needs `marketkit[plot]`) |
| `compare(tickers, *, metrics=None, period="1y", **kw)` | `DataFrame` | Metrics table across several tickers |
| `screen(tickers, *, filters, period="1y", **kw)` | `DataFrame` | Filter tickers by predicates over their metrics |
| `Ticker(symbol, **kw)` | `Ticker` | Fetches once, exposes analytics/plotting as methods |
| `df.mk.*` | — | Pandas accessor exposing the same analytics/plotting as `df.mk.sharpe()`, `df.mk.plot()`, etc. |

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
