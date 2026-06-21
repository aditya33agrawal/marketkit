# marketkit — Feature Roadmap & Release Plan

This is the forward-looking plan: the features we want to add, the order to ship
them in, the public API each one introduces, and reference implementations for
the tricky math. It complements [`tech-plan.md`](tech-plan.md), which describes
the architecture that already exists (v0.1.x).

The two themes driving everything below:

1. **Give users more ways to plot** — charts should be a one-liner, with sensible
   defaults, working on a bare `df` straight out of `mk.get()`.
2. **Give users more market math** — the common technical, statistical, and risk
   functions that quants and hobbyists reach for, all pure-Python, all on the
   same canonical data contract.

A third theme runs underneath: **keep it easy.** Every addition must work on the
frame `mk.get()` already returns, keep the "learn it in five minutes" surface,
and never force a heavy dependency on someone who just wants data.

---

## Guiding principles (don't break these)

- **Pure-Python install stays the default.** Plotting, extra sources, and any
  heavyweight dependency go behind `pip install marketkit[...]` extras. `pip
  install marketkit` must keep working on locked-down CI with no compiler.
- **One data contract.** Everything consumes/returns the canonical OHLCV frame
  (or a bare price `Series`) defined in `tech-plan.md` §0. New indicators follow
  the existing `_px(data, column=...)` convention so they compose freely.
- **Typed + tested.** Every new function ships with type hints, passes
  `mypy --strict`, and has hand-computed unit tests (analytics) or replayed
  fixtures (sources). No network in CI.
- **Additive, backward-compatible.** Until 1.0 we can extend, but we don't break
  signatures already documented in the README. New args are keyword-only with
  defaults.
- **Beginner-first ergonomics.** A new user should reach a useful chart and a
  useful number in three lines. Power-user knobs exist but never get in the way.

---

## Release overview

| Version | Theme | Headline |
|---|---|---|
| **0.2.0** | Plotting foundation | `mk.plot()`, candlesticks, indicator overlays — optional `[plot]` extra |
| **0.3.0** | Market math expansion | ATR, Stochastics, ADX, OBV, VWAP, Ichimoku, Keltner/Donchian, more MAs |
| **0.4.0** | Statistical & risk math | beta/alpha, VaR/CVaR, Calmar/Omega, rolling metrics, z-score, regression channel |
| **0.5.0** | Ergonomics | pandas `.mk` accessor, `Ticker` object, `compare()`/`screen()`, CLI |
| **0.6.0** | Data layer | intraday, crypto/FX, async multi-fetch, `resample()`, optional fundamentals |
| **0.7.0** | Signals & charts++ | signal helpers, interactive Plotly backend, tear-sheet report |
| **1.0.0** | Stability | API freeze, full docs site, performance pass |

Ship each only when its tests pass and the README/docs are updated in the same
PR. Resist pulling later items forward unless a user actually asks.

---

## 0.2.0 — Plotting foundation

**Goal:** make charting a one-liner. Today users have to hand-roll matplotlib in
the notebook. We give them a small, opinionated plotting layer that understands
the canonical frame and the indicators we already ship.

### Packaging

- New optional extra in `pyproject.toml`:
  ```toml
  [project.optional-dependencies]
  plot = ["matplotlib>=3.5"]
  ```
- New module `src/marketkit/plot.py`. On import it tries `import matplotlib`; if
  missing, every plot function raises a clear `MarketkitError` subclass
  `PlottingUnavailable` with the message *"Plotting needs matplotlib — install
  with `pip install marketkit[plot]`."* (Don't crash at package import; only when
  a plot function is actually called.)
- Re-export the public plot functions from `marketkit/__init__.py` so
  `mk.plot(...)` works, but guard the heavy import so the base package stays
  light (lazy import inside the functions).

### Public API

| Function | Returns | Description |
|---|---|---|
| `plot(data, *, kind="line", column="adj_close", indicators=None, ax=None, **kw)` | `Axes` | The one-liner. Line or candlestick price chart, optionally overlaying named indicators. |
| `candlestick(data, *, volume=True, ax=None)` | `Axes` | OHLC candlestick with optional volume sub-panel. |
| `plot_indicators(data, indicators, *, ax=None)` | `Axes`/`list[Axes]` | Overlay/stack indicators (SMA/EMA/Bollinger on price; RSI/MACD in their own panel). |
| `plot_drawdown(data, *, ax=None)` | `Axes` | Underwater (drawdown) curve from `risk.drawdown`. |
| `plot_returns(data, *, kind="hist", ax=None)` | `Axes` | Returns distribution histogram, or cumulative-growth line. |
| `plot_correlation(frames, *, ax=None)` | `Axes` | Correlation heatmap across multiple tickers (from a wide frame or dict). |

### Design notes

- **Always return the `Axes`** so users can keep customizing (titles, save).
  Never call `plt.show()` inside the library — that's the caller's job (and it
  breaks in headless CI). Accept an optional `ax=` so plots compose into
  subplots.
- **Indicator overlays by name.** `indicators=["sma:50", "ema:20", "bollinger"]`
  — parse `"name:param"` strings, dispatch to the existing indicator functions,
  and plot price-overlay indicators on the main axis while panel indicators
  (RSI, MACD) get their own stacked sub-axes. This keeps the call short and
  discoverable.
- **Candlesticks without mplfinance.** Draw with `matplotlib` primitives
  (vlines for wicks, bars for bodies) so we don't add another dependency. Up/down
  colors configurable; default green/red with colorblind-friendly option.
- **Works on multi-ticker frames.** If a `ticker` column (long) or column
  MultiIndex (wide) is present, `plot()` overlays each ticker's price (normalized
  to 100 at the start by default via `rebase=True`) — the natural "compare these
  symbols" chart.

### Reference sketch

```python
# plot.py (sketch — full version handles panels, multi-ticker, candlesticks)
from __future__ import annotations
from typing import Any, Sequence
import pandas as pd
from marketkit.errors import MarketkitError

class PlottingUnavailable(MarketkitError):
    """matplotlib isn't installed; run `pip install marketkit[plot]`."""

def _mpl():
    try:
        import matplotlib.pyplot as plt
    except ImportError as e:  # pragma: no cover
        raise PlottingUnavailable(
            "Plotting needs matplotlib — install with `pip install marketkit[plot]`."
        ) from e
    return plt

def plot(data, *, kind="line", column="adj_close",
         indicators: Sequence[str] | None = None, ax=None, **kw) -> Any:
    plt = _mpl()
    ax = ax or plt.subplots(figsize=(10, 5))[1]
    if kind == "candle":
        return candlestick(data, ax=ax, **kw)
    ax.plot(data.index, data[column], label=column)
    if indicators:
        _overlay(ax, data, indicators)
    ax.set_xlabel("date"); ax.legend(); return ax
```

### Tests

- Use the `Agg` backend (`matplotlib.use("Agg")`) so tests run headless.
- Assert each function returns an `Axes` and that the expected number of lines /
  patches were drawn (e.g. `len(ax.lines)`), not pixel output.
- Assert `PlottingUnavailable` is raised cleanly when matplotlib is monkeypatched
  to be absent.

### Docs

- New `examples/plotting.ipynb` walkthrough.
- README: a "Plotting" section with 3–4 copy-paste snippets and one screenshot.

---

## 0.3.0 — Market math expansion (technical indicators)

**Goal:** cover the indicators people expect from a TA library, all pure
pandas/numpy, all on the existing contract. Each returns a `Series` or labeled
`DataFrame` you can assign back or hand to `plot()`.

Add to `analytics/indicators.py` (or split into `indicators/` if the file grows):

| Function | Returns | Notes |
|---|---|---|
| `wma(data, window=20)` | `Series` | Linearly weighted MA. |
| `hma(data, window=20)` | `Series` | Hull MA (low-lag). |
| `dema(data, window=20)` / `tema(...)` | `Series` | Double/triple EMA. |
| `atr(data, period=14)` | `Series` | Average True Range (needs OHLC). |
| `true_range(data)` | `Series` | Building block for ATR/Keltner. |
| `stochastic(data, k=14, d=3)` | `DataFrame` | `%K`, `%D` oscillator. |
| `williams_r(data, period=14)` | `Series` | Williams %R. |
| `cci(data, period=20)` | `Series` | Commodity Channel Index. |
| `adx(data, period=14)` | `DataFrame` | `adx`, `+di`, `-di` trend strength. |
| `roc(data, period=12)` / `momentum(...)` | `Series` | Rate of change / momentum. |
| `obv(data)` | `Series` | On-Balance Volume (needs volume). |
| `vwap(data)` | `Series` | Volume-weighted average price. |
| `mfi(data, period=14)` | `Series` | Money Flow Index. |
| `keltner(data, window=20, k=2)` | `DataFrame` | Keltner channels (EMA ± k·ATR). |
| `donchian(data, window=20)` | `DataFrame` | Donchian channels (rolling high/low). |
| `ichimoku(data)` | `DataFrame` | Tenkan/Kijun/Senkou A,B/Chikou. |
| `psar(data, step=0.02, max_step=0.2)` | `Series` | Parabolic SAR. |

### Implementation guardrails (the silent-bug spots)

- **ATR / ADX use Wilder smoothing** (`ewm(alpha=1/period, adjust=False)`), same
  as the existing RSI — be consistent, document it.
- **OHLC-dependent indicators** (ATR, stochastic, ADX, CCI, Williams %R) must
  accept a `DataFrame`, not a bare `Series`. Raise `InvalidRequest` with a clear
  message if handed a Series (or only `close`). Keep the `_px` helper for the
  close-only ones.
- **Division-by-zero** (flat price windows): produce `NaN`, never raise.

### Reference: ATR + Stochastic

```python
def true_range(data, *, high="high", low="low", close="close"):
    h, l, c = data[high], data[low], data[close]
    prev = c.shift(1)
    return pd.concat([h - l, (h - prev).abs(), (l - prev).abs()], axis=1).max(axis=1)

def atr(data, period=14):
    return true_range(data).ewm(alpha=1/period, adjust=False).mean()  # Wilder

def stochastic(data, k=14, d=3):
    low_k = data["low"].rolling(k).min()
    high_k = data["high"].rolling(k).max()
    pct_k = 100 * (data["close"] - low_k) / (high_k - low_k)
    return pd.DataFrame({"%K": pct_k, "%D": pct_k.rolling(d).mean()})
```

### Tests

Hand-compute each on a tiny fixed series (e.g. closes `[100,110,105,120,115]`,
with matching OHLC) and assert to a tolerance. This is where correctness bugs
hide — be thorough, especially Wilder vs simple smoothing.

---

## 0.4.0 — Statistical & risk math

**Goal:** the quantitative/statistical functions people use to evaluate a series
or compare it to a benchmark. Extend `analytics/risk.py` and add
`analytics/stats.py`.

### Risk / performance (in `risk.py`)

| Function | Returns | Notes |
|---|---|---|
| `calmar(data, *, periods_per_year=252)` | `float` | CAGR / |max drawdown|. |
| `omega(data, *, threshold=0.0)` | `float` | Omega ratio. |
| `var(data, *, level=0.05, method="historical")` | `float` | Value at Risk (historical or Gaussian). |
| `cvar(data, *, level=0.05)` | `float` | Conditional VaR (expected shortfall). |
| `downside_deviation(data, *, mar=0.0)` | `float` | For Sortino internals + standalone. |
| `ulcer_index(data)` | `float` | Drawdown-based risk. |
| `rolling_sharpe(data, *, window=63, **kw)` | `Series` | Time-varying Sharpe. |
| `rolling_volatility(data, *, window=21, **kw)` | `Series` | Plots straight into `plot()`. |

### Benchmark-relative (in `stats.py`)

| Function | Returns | Notes |
|---|---|---|
| `beta(data, benchmark, **kw)` | `float` | Slope of asset vs benchmark returns. |
| `alpha(data, benchmark, *, rf=0.0, **kw)` | `float` | Jensen's alpha (annualized). |
| `correlation(data, benchmark, **kw)` | `float` | Returns correlation. |
| `tracking_error(data, benchmark, **kw)` | `float` | Std of return difference. |
| `information_ratio(data, benchmark, **kw)` | `float` | Active return / tracking error. |
| `rolling_beta(data, benchmark, *, window=63)` | `Series` | Time-varying beta. |

### Pure-statistical transforms (in `stats.py`)

| Function | Returns | Notes |
|---|---|---|
| `zscore(data, *, window=None, column="close")` | `Series` | Rolling or full-sample standardization (mean-reversion signal). |
| `normalize(data, *, base=100, column="adj_close")` | `Series` | Rebase to a starting value — the comparison-chart helper. |
| `autocorr(data, *, lags=20, **kw)` | `Series` | Return autocorrelation by lag. |
| `linreg_channel(data, *, window=100, k=2)` | `DataFrame` | Least-squares trend line ± k·std band. |
| `hurst(data, **kw)` | `float` | Hurst exponent (trending vs mean-reverting). |
| `rolling_corr(frames, *, window=63)` | `DataFrame` | Pairwise rolling correlation across tickers. |

### Guardrails

- Benchmark-relative functions must **align indices** (inner join on date) before
  computing — mismatched calendars are the classic source of garbage betas.
- VaR/CVaR sign convention documented clearly (return a positive loss magnitude
  or a negative number — pick one, say so, test it).
- All accept the same `kind`/`column` kwargs as `returns()` for consistency.

### Reference: beta + historical VaR

```python
def beta(data, benchmark, **kw):
    a, b = returns(data, **kw).align(returns(benchmark, **kw), join="inner")
    return float(a.cov(b) / b.var())

def var(data, *, level=0.05, method="historical", **kw):
    r = returns(data, **kw)
    if method == "gaussian":
        from scipy.stats import norm  # optional; or use numpy quantile fallback
        return float(-(r.mean() + norm.ppf(level) * r.std(ddof=1)))
    return float(-r.quantile(level))  # historical
```

> Note: prefer a numpy-only implementation (`np.quantile`, manual Gaussian) to
> avoid adding `scipy`. If a few functions genuinely need scipy, gate them behind
> a `[stats]` extra rather than the base install.

---

## 0.5.0 — Ergonomics (make it effortless)

**Goal:** cut the boilerplate. Same engine, friendlier front doors.

### pandas accessor — `df.mk`

Register a `.mk` accessor so analytics chain off any canonical frame:

```python
df = mk.get("RELIANCE.NS")
df.mk.rsi()                 # -> Series
df.mk.sharpe(rf=0.04)       # -> float
df.mk.plot(indicators=["sma:50", "bollinger"])
df.mk.summary()            # -> Series
```

Implement with `@pd.api.extensions.register_dataframe_accessor("mk")`. The
accessor just forwards to the existing functions — zero logic duplication.

### `Ticker` object (optional, discoverable)

```python
t = mk.Ticker("RELIANCE.NS", period="5y")
t.df            # cached canonical frame
t.rsi()         # indicator
t.summary()     # report
t.plot()        # chart
```

A thin wrapper holding the fetched frame + lazy methods. Good for tab-completion
discovery; the functional API stays first-class.

### Comparison & screening

| Function | Returns | Description |
|---|---|---|
| `compare(tickers, *, metric="cagr", period="1y", **kw)` | `DataFrame` | Side-by-side metrics table across tickers. |
| `screen(tickers, *, filters, period="1y")` | `DataFrame` | Filter a universe by metric thresholds (e.g. `sharpe > 1, max_drawdown > -0.2`). |

### CLI

A small `marketkit` console entry point (`[project.scripts]`):

```bash
marketkit get RELIANCE.NS --period 5y --out reliance.csv
marketkit summary RELIANCE.NS
marketkit plot RELIANCE.NS --indicators sma:50,rsi --save chart.png
```

Built on `argparse` (stdlib — no new dep). Great for non-programmers and quick
shell use.

---

## 0.6.0 — Data layer expansion

**Goal:** more of what to fetch and how, without breaking the contract.

- **Intraday intervals** (`1m`, `5m`, `15m`, `1h`) via Yahoo, with documented
  history limits and intraday-aware cache TTLs (short series go stale fast).
- **Crypto & FX** symbol handling (`BTC-USD`, `EURUSD=X`) — mostly a docs +
  symbol-normalization task on top of existing sources.
- **Async / concurrent multi-ticker fetch** — replace the sequential loop in
  `fetch.get()` with a bounded thread pool (stdlib `concurrent.futures`) for big
  universes. Keep the sync signature; parallelism is internal.
- **`resample(df, interval)`** — convert daily → weekly/monthly with correct
  OHLCV aggregation (`open=first, high=max, low=min, close=last, volume=sum`).
- **Optional fundamentals** (`info()` / `dividends()` / `splits()`) — gated, best
  effort, clearly labeled as unofficial; never required for the core path.
- **Pluggable sources** — document the `Source` protocol publicly so users can
  register their own (e.g. a broker API) via `sources.register(...)`.

---

## 0.7.0 — Signals, reports & interactive charts

- **Signal helpers** — `crossover(a, b)`, `crossunder(a, b)`, and a tiny
  `signals.golden_cross(df)` / `rsi_oversold(df)` set returning boolean Series.
  Explicitly *not* a backtester — just the building blocks, with a clear "this is
  not financial advice / not a backtest" note.
- **Tear sheet** — `mk.report(ticker)` produces a one-call multi-panel figure
  (price+MAs, drawdown, returns histogram, rolling Sharpe) and a metrics table.
- **Interactive Plotly backend** — optional `[plotly]` extra; `plot(...,
  backend="plotly")` returns a Plotly figure for notebooks/dashboards. The
  matplotlib backend stays the default and the only required one.

---

## 1.0.0 — Stability

- Freeze the public API (everything in `__all__`); adopt deprecation warnings for
  any future change.
- Full docs site (mkdocs-material, already in the `[docs]` extra) with an API
  reference, an indicators gallery, and a plotting gallery.
- Performance pass on `fetch`/`cache` for large universes.
- Coverage ≥ 90%; property-based tests for the math (hypothesis) where it helps.

---

## Cross-cutting: keeping it easy as we grow

- **Extras, not bloat.** `marketkit` (core) → `[plot]` → `[plotly]` → `[stats]` →
  `[all]`. Document the matrix in the README so users install only what they need.
- **Consistent kwargs.** `column=`, `kind=`, `periods_per_year=` mean the same
  thing everywhere. A new indicator that invents its own naming is a bug.
- **Errors teach.** Every new failure mode raises a typed `MarketkitError`
  subclass with a message that tells the user the fix (e.g. which extra to
  install, which column is missing).
- **Docs ship with code.** No feature merges without README/notebook coverage in
  the same PR. Update `CHANGELOG.md` every release.
- **`__all__` is the contract.** If it's exported, it's tested, typed, and
  documented.

---

## Suggested immediate next steps

1. Land the **0.2.0 plotting foundation** first — it's the highest-visibility,
   most-requested capability and unlocks compelling examples/screenshots that
   help adoption.
2. In parallel (independent of the data layer), expand **0.3.0 indicators** —
   they're pure functions, fully testable offline, and feed directly into the new
   plots.
3. Decide the plotting backend posture now: **matplotlib as the required default,
   Plotly as a later optional extra** (recommended) keeps the install light while
   leaving the interactive door open.
