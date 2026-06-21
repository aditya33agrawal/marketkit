import pandas as pd
import pytest

from marketkit import clean, ticker as ticker_mod


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


@pytest.fixture(autouse=True)
def patched_get(monkeypatch):
    monkeypatch.setattr(ticker_mod, "get", lambda *a, **kw: _frame())


def test_ticker_fetches_once_and_exposes_df():
    t = ticker_mod.Ticker("aapl")
    assert t.symbol == "AAPL"
    assert not t.df.empty


def test_ticker_methods_forward_to_module_functions():
    t = ticker_mod.Ticker("aapl")
    assert isinstance(t.rsi(), pd.Series)
    assert isinstance(t.sharpe(), float)
    out = t.summary()
    assert out["ticker"] == "AAPL"


def test_ticker_repr():
    t = ticker_mod.Ticker("aapl")
    assert "AAPL" in repr(t)


def test_ticker_remaining_forwarders():
    t = ticker_mod.Ticker("aapl")
    assert isinstance(t.returns(), pd.Series)
    assert isinstance(t.cagr(), float)
    assert isinstance(t.volatility(), float)
    assert isinstance(t.sortino(), float)
    dd, max_dd = t.drawdown()
    assert isinstance(dd, pd.Series) and isinstance(max_dd, float)
    assert isinstance(t.sma(), pd.Series)
    assert isinstance(t.macd(), pd.DataFrame)
    assert isinstance(t.bollinger(), pd.DataFrame)


def test_ticker_plot():
    import matplotlib

    matplotlib.use("Agg")
    t = ticker_mod.Ticker("aapl")
    ax = t.plot(column="close")
    assert len(ax.lines) == 1
