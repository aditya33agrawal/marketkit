# marketkit

Reliable, clean market data and analytics — pure Python, no C dependencies.

See the [README](https://github.com/aditya33agrawal/marketkit#readme) for the
full quick start, feature tour, and configuration reference. This site adds:

- an [API reference](api.md) generated from docstrings
- the internal [architecture / data contract](tech-plan.md)
- the [feature roadmap](roadmap.md)

```bash
pip install marketkit
```

```python
import marketkit as mk

df = mk.get("RELIANCE.NS", period="2y")
mk.sharpe(df)
mk.plot(df, indicators=["sma:50", "rsi"])
```
