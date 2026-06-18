# marketkit

Reliable, clean market data and basic analytics, pure Python, no C dependencies.

## Install

pip install marketkit

## Quick start

import marketkit as mk

# Fetch clean, adjusted OHLCV data
df = mk.get("AAPL")

# Analytics
print(mk.sharpe(df))
print(mk.drawdown(df))

# Indicators
df["rsi"] = mk.rsi(df)
df["sma50"] = mk.sma(df, window=50)

# One-shot summary
mk.summary("AAPL")

## Why marketkit?

- Pure Python — installs with plain `pip install`, no compiler needed
- Doesn't break — automatic source fallback + caching so one bad day from Yahoo doesn't crash your script
- Clean output — flat columns, predictable dtypes, adjusted prices by default
- Beginner-friendly — sensible defaults, clear errors, great docs

## Disclaimer

Not affiliated with any data provider. Data is for personal/research use only.
Users must comply with each source's terms of service. Not financial advice.
