# Changelog

## 1.0.0

First stable release. Implements the full feature set from
[`docs/roadmap.md`](docs/roadmap.md) (0.2.0 through 0.7.0) in one pass, plus
a stability/polish pass to close out 1.0.0.

### Added

- **Plotting** (`marketkit[plot]` / `marketkit[plotly]`, optional): `plot()`,
  `candlestick()`, `plot_indicators()` (stacked overlay/panel charts driven by
  string specs like `"sma:50"`, `"macd:12,26,9"`), `plot_drawdown()`,
  `plot_returns()`, `plot_correlation()`. Matplotlib is the default backend;
  pass `backend="plotly"` for interactive charts. Multi-ticker frames can be
  rebased to a common starting value with `rebase=True`.
- **Indicators**: `wma`, `hma`, `dema`, `tema`, `true_range`, `atr`,
  `stochastic`, `williams_r`, `cci`, `adx`, `roc`, `momentum`, `obv`, `vwap`,
  `mfi`, `keltner`, `donchian`, `ichimoku`, `psar` — alongside the existing
  `sma`, `ema`, `rsi`, `macd`, `bollinger`.
- **Risk & statistics**: `calmar`, `omega`, `var` (historical or Gaussian),
  `cvar`, `downside_deviation`, `ulcer_index`, `rolling_sharpe`,
  `rolling_volatility`, `beta`, `alpha`, `correlation`, `tracking_error`,
  `information_ratio`, `rolling_beta`, `zscore`, `normalize`, `autocorr`,
  `linreg_channel`, `hurst`, `rolling_corr`.
- **Ergonomics**: a `.mk` pandas accessor (`df.mk.sharpe()`, `df.mk.plot()`,
  ...) registered on import; a `Ticker` class that fetches once and exposes
  all analytics/plotting as methods; `compare()` and `screen()` for
  multi-ticker metrics tables and predicate-based filtering; a `marketkit`
  console script (`marketkit get|summary|plot`).
- **Data layer**: intraday intervals (`1m`/`5m`/`15m`/`30m`/`1h`) with a
  shorter 5-minute cache TTL, `resample()` for converting daily bars to
  weekly/monthly, and concurrent (thread-pooled) fetching for multi-ticker
  requests.
- **Signals & reports**: `crossover`/`crossunder`/`golden_cross`/
  `death_cross`/`rsi_oversold`/`rsi_overbought` boolean signal helpers (not a
  backtester), and `report()` for a one-call 4-panel tear sheet.
- New optional-dependency extras: `[plot]`, `[plotly]`, `[stats]`, `[all]`.
  The base install stays pure-Python; all of the above import their
  dependencies lazily and raise `PlottingUnavailable` /
  `OptionalDependencyMissing` with an install hint if missing.

### Notes

- No breaking changes to the existing data contract, `get()`, `summary()`, or
  the original returns/risk/indicator functions — this release is purely
  additive.

## 0.1.3

- Also ignore missing type stubs for `requests` under mypy strict mode
  (CI's Python 3.9 job didn't have requests' bundled types resolved the
  same way the dev environment did). No behavior change.

## 0.1.2

- Fix `mypy --strict` failures (missing annotations, untyped pandas
  imports, unsupported `python_version`) that broke CI for the `v0.1.1`
  tag before it could publish. No behavior change.

## 0.1.1

- First functional release. The `0.1.0` tag/PyPI upload shipped only empty
  module stubs; this release implements the actual package per
  `docs/tech-plan.md`: clean-data contract, Yahoo/Stooq sources with
  fallback, Parquet cache, fetch orchestration, returns/risk/indicator
  analytics, and `summary()`.

## 0.1.0

- Initial (non-functional) scaffold.
