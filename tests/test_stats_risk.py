import numpy as np
import pandas as pd
import pytest

from marketkit.analytics.returns import returns
from marketkit.analytics.risk import (
    calmar, cvar, downside_deviation, omega, rolling_sharpe, rolling_volatility,
    ulcer_index, var,
)
from marketkit.analytics.stats import (
    alpha, autocorr, beta, correlation, hurst, information_ratio, linreg_channel,
    normalize, rolling_beta, rolling_corr, tracking_error, zscore,
)

CLOSES = [100, 102, 101, 105, 103, 108, 104, 110, 107, 112, 109, 115]


@pytest.fixture
def series():
    return pd.Series(CLOSES, index=pd.date_range("2024-01-01", periods=len(CLOSES)))


@pytest.fixture
def benchmark():
    bench = [200 * (1 + 0.5 * (c / 100 - 1)) for c in CLOSES]  # half the asset's moves
    return pd.Series(bench, index=pd.date_range("2024-01-01", periods=len(bench)))


def test_calmar_matches_cagr_over_max_drawdown(series):
    from marketkit.analytics.returns import cagr
    from marketkit.analytics.risk import drawdown

    expected = cagr(series) / abs(drawdown(series)[1])
    assert calmar(series) == pytest.approx(expected)


def test_calmar_zero_drawdown_returns_inf_not_zero_division():
    monotonic = pd.Series(range(100, 120), index=pd.date_range("2024-01-01", periods=20))
    assert calmar(monotonic) == float("inf")


def test_omega_positive_for_uptrend(series):
    assert omega(series) > 1


def test_var_historical_matches_quantile(series):
    r = returns(series)
    expected = -r.quantile(0.05)
    assert var(series, level=0.05) == pytest.approx(expected)


def test_var_gaussian_close_to_historical_for_normal_ish_data(series):
    hist = var(series, level=0.05, method="historical")
    gauss = var(series, level=0.05, method="gaussian")
    assert gauss == pytest.approx(hist, abs=0.05)


def test_cvar_worse_than_var(series):
    v = var(series, level=0.2)
    cv = cvar(series, level=0.2)
    assert cv >= v


def test_downside_deviation_nonnegative(series):
    assert downside_deviation(series) >= 0


def test_ulcer_index_nonnegative(series):
    assert ulcer_index(series) >= 0


def test_rolling_sharpe_and_volatility_have_nan_head(series):
    rs = rolling_sharpe(series, window=5)
    rv = rolling_volatility(series, window=5)
    assert rs.iloc[:3].isna().all()
    assert rv.iloc[:3].isna().all()
    assert rs.dropna().shape[0] > 0


def test_beta_one_for_identical_series(series):
    assert beta(series, series) == pytest.approx(1.0)


def test_beta_half_for_half_moves(series, benchmark):
    # asset moves are ~2x benchmark moves by construction -> beta of asset vs bench ~2
    b = beta(series, benchmark)
    assert b == pytest.approx(2.0, rel=0.2)


def test_alpha_zero_for_identical_series(series):
    assert alpha(series, series, rf=0.0) == pytest.approx(0.0, abs=1e-6)


def test_correlation_one_for_identical_series(series):
    assert correlation(series, series) == pytest.approx(1.0)


def test_tracking_error_zero_for_identical_series(series):
    assert tracking_error(series, series) == pytest.approx(0.0, abs=1e-9)


def test_information_ratio_runs(series, benchmark):
    ir = information_ratio(series, benchmark)
    assert np.isfinite(ir)


def test_rolling_beta_runs(series, benchmark):
    rb = rolling_beta(series, benchmark, window=5)
    assert rb.dropna().shape[0] > 0


def test_zscore_full_sample_mean_zero(series):
    df = series.to_frame("close")
    z = zscore(df)
    assert z.mean() == pytest.approx(0.0, abs=1e-9)
    assert z.std(ddof=1) == pytest.approx(1.0)


def test_zscore_rolling_has_nan_head(series):
    df = series.to_frame("close")
    z = zscore(df, window=5)
    assert z.iloc[:4].isna().all()


def test_normalize_starts_at_base(series):
    df = series.to_frame("adj_close")
    out = normalize(df, base=100)
    assert out.iloc[0] == pytest.approx(100.0)
    assert out.iloc[-1] == pytest.approx(CLOSES[-1] / CLOSES[0] * 100)


def test_autocorr_lag_count(series):
    out = autocorr(series, lags=5)
    assert len(out) == 5
    assert list(out.index) == [1, 2, 3, 4, 5]


def test_linreg_channel_band_order(series):
    df = series.to_frame("close")
    out = linreg_channel(df, window=5, k=2)
    valid = out.dropna()
    assert (valid["upper"] >= valid["mid"]).all()
    assert (valid["lower"] <= valid["mid"]).all()


def test_hurst_runs_on_trending_series():
    trend = pd.Series(np.arange(200, dtype="float64") + np.random.RandomState(0).normal(0, 0.1, 200))
    h = hurst(trend.to_frame("close"), max_lag=50)
    assert 0.0 < h < 1.5  # trending series should skew above 0.5, loosely bounded


def test_rolling_corr_pairs(series, benchmark):
    out = rolling_corr({"a": series, "b": benchmark}, window=5)
    assert ("a", "b") in out.columns
    assert out.dropna().shape[0] > 0
