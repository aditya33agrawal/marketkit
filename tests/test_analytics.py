import numpy as np
import pandas as pd
import pytest

from marketkit.analytics.indicators import bollinger, ema, macd, rsi, sma
from marketkit.analytics.returns import cagr, returns
from marketkit.analytics.risk import drawdown, sharpe, sortino, volatility

CLOSES = [100, 110, 105, 120]


@pytest.fixture
def series():
    return pd.Series(CLOSES, index=pd.date_range("2024-01-01", periods=len(CLOSES)))


def test_returns_simple(series):
    r = returns(series)
    expected = pd.Series(CLOSES).pct_change().dropna()
    np.testing.assert_allclose(r.values, expected.values)


def test_returns_log(series):
    r = returns(series, kind="log")
    expected = np.log(pd.Series(CLOSES) / pd.Series(CLOSES).shift(1)).dropna()
    np.testing.assert_allclose(r.values, expected.values)


def test_cagr(series):
    result = cagr(series, periods_per_year=252)
    total = CLOSES[-1] / CLOSES[0]
    expected = total ** (252 / len(CLOSES)) - 1
    assert result == pytest.approx(expected)


def test_volatility(series):
    r = returns(series)
    expected = r.std(ddof=1) * np.sqrt(252)
    assert volatility(series) == pytest.approx(expected)


def test_sharpe_zero_rf(series):
    r = returns(series)
    expected = (r.mean() / r.std(ddof=1)) * np.sqrt(252)
    assert sharpe(series, rf=0.0) == pytest.approx(expected)


def test_sortino():
    # needs at least two down-periods so downside std(ddof=1) isn't NaN
    closes = [100, 110, 105, 120, 90, 95]
    s = pd.Series(closes, index=pd.date_range("2024-01-01", periods=len(closes)))
    r = returns(s)
    downside = r[r < 0].std(ddof=1)
    expected = (r.mean() / downside) * np.sqrt(252)
    assert sortino(s, rf=0.0) == pytest.approx(expected)


def test_drawdown(series):
    r = returns(series)
    curve = (1 + r).cumprod()
    peak = curve.cummax()
    expected_dd = curve / peak - 1
    dd, max_dd = drawdown(series)
    np.testing.assert_allclose(dd.values, expected_dd.values)
    assert max_dd == pytest.approx(expected_dd.min())
    # 110 -> 105 is the only drawdown in this series
    assert max_dd == pytest.approx(105 / 110 - 1)


def test_sma(series):
    df = series.to_frame("close")
    out = sma(df, window=2)
    assert np.isnan(out.iloc[0])
    assert out.iloc[1] == pytest.approx((100 + 110) / 2)
    assert out.iloc[2] == pytest.approx((110 + 105) / 2)


def test_ema(series):
    df = series.to_frame("close")
    out = ema(df, window=2)
    # ewm(span=2, adjust=False): alpha = 2/(2+1)
    alpha = 2 / 3
    expected = [100]
    for px in CLOSES[1:]:
        expected.append(alpha * px + (1 - alpha) * expected[-1])
    np.testing.assert_allclose(out.values, expected)


def test_rsi_matches_wilder_smoothing_definition():
    closes = [44, 44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84,
              46.08, 45.89, 46.03, 45.61, 46.28, 46.28]
    px = pd.Series(closes)
    df = px.to_frame("close")
    out = rsi(df, period=14)

    delta = px.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / 14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / 14, adjust=False).mean()
    expected = 100 - 100 / (1 + avg_gain / avg_loss)

    np.testing.assert_allclose(out.values, expected.values)
    assert (out.dropna() >= 0).all() and (out.dropna() <= 100).all()


def test_macd_shape(series):
    df = series.to_frame("close")
    out = macd(df, fast=2, slow=3, signal=2)
    assert list(out.columns) == ["macd", "signal", "hist"]
    np.testing.assert_allclose(
        out["hist"].values, (out["macd"] - out["signal"]).values
    )


def test_bollinger_bands_straddle_mid():
    df = pd.Series(CLOSES).to_frame("close")
    out = bollinger(df, window=2, k=2)
    valid = out.dropna()
    assert (valid["upper"] >= valid["mid"]).all()
    assert (valid["lower"] <= valid["mid"]).all()


def test_indicators_short_series_return_nan_head():
    df = pd.Series([1.0, 2.0]).to_frame("close")
    out = sma(df, window=5)
    assert out.isna().all()
