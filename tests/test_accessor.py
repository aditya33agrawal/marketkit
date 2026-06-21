import pandas as pd

from marketkit import accessor  # noqa: F401  (registers the accessor)
from marketkit import clean


def _frame():
    idx = pd.date_range("2024-01-01", periods=20)
    raw = pd.DataFrame(
        {
            "Open": range(20),
            "High": range(20),
            "Low": range(20),
            "Close": [100 + i for i in range(20)],
            "Volume": [100] * 20,
        },
        index=idx,
    )
    return clean.normalize(raw, source="yahoo")


def test_mk_accessor_rsi_and_sharpe():
    df = _frame()
    assert isinstance(df.mk.rsi(), pd.Series)
    assert isinstance(df.mk.sharpe(), float)


def test_mk_accessor_summary():
    df = _frame()
    out = df.mk.summary()
    assert "cagr" in out.index


def test_mk_accessor_zscore_and_normalize():
    df = _frame()
    assert isinstance(df.mk.zscore(), pd.Series)
    assert isinstance(df.mk.normalize(), pd.Series)


def test_mk_accessor_remaining_forwarders():
    df = _frame()
    assert isinstance(df.mk.returns(), pd.Series)
    assert isinstance(df.mk.cagr(), float)
    assert isinstance(df.mk.volatility(), float)
    assert isinstance(df.mk.sortino(), float)
    dd, max_dd = df.mk.drawdown()
    assert isinstance(dd, pd.Series) and isinstance(max_dd, float)
    assert isinstance(df.mk.calmar(), float)
    assert isinstance(df.mk.var(), float)
    assert isinstance(df.mk.cvar(), float)
    assert isinstance(df.mk.ema(), pd.Series)
    assert isinstance(df.mk.macd(), pd.DataFrame)
    assert isinstance(df.mk.bollinger(), pd.DataFrame)
    assert isinstance(df.mk.atr(), pd.Series)


def test_mk_accessor_plot():
    import matplotlib

    matplotlib.use("Agg")
    df = _frame()
    ax = df.mk.plot(column="close")
    assert len(ax.lines) == 1
