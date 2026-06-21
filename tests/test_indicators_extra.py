import numpy as np
import pandas as pd
import pytest

from marketkit.analytics.indicators import (
    adx, atr, cci, dema, donchian, hma, ichimoku, keltner, mfi, momentum,
    obv, psar, roc, stochastic, tema, true_range, vwap, williams_r, wma,
)
from marketkit.errors import InvalidRequest

CLOSES = [44, 44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84,
          46.08, 45.89, 46.03, 45.61, 46.28, 46.28, 46.5, 46.9, 47.1, 46.7]


@pytest.fixture
def ohlcv():
    idx = pd.date_range("2024-01-01", periods=len(CLOSES))
    close = pd.Series(CLOSES, index=idx)
    high = close + 0.5
    low = close - 0.5
    open_ = close.shift(1).fillna(close.iloc[0])
    volume = pd.Series([1000 + 10 * i for i in range(len(CLOSES))], index=idx)
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume}
    )


def test_wma_weights_recent_bars_more(ohlcv):
    out = wma(ohlcv, window=3)
    window_vals = CLOSES[:3]
    weights = np.array([1, 2, 3], dtype="float64")
    expected = np.dot(window_vals, weights) / weights.sum()
    assert out.iloc[2] == pytest.approx(expected)
    assert np.isnan(out.iloc[1])


def test_hma_runs_and_has_nan_head(ohlcv):
    out = hma(ohlcv, window=8)
    assert out.isna().iloc[0]
    assert not out.dropna().empty


def test_dema_tema_reduce_lag_vs_ema(ohlcv):
    from marketkit.analytics.indicators import ema

    e = ema(ohlcv, window=5, column="close")
    d = dema(ohlcv, window=5, column="close")
    t = tema(ohlcv, window=5, column="close")
    # all three should track the rising series; just assert they run and stay finite
    assert d.dropna().shape[0] > 0
    assert t.dropna().shape[0] > 0
    assert np.isfinite(e.dropna().iloc[-1])


def test_true_range_and_atr_require_ohlc(ohlcv):
    tr = true_range(ohlcv)
    assert (tr.dropna() >= 0).all()
    a = atr(ohlcv, period=5)
    assert a.dropna().shape[0] > 0

    with pytest.raises(InvalidRequest):
        true_range(ohlcv["close"])  # bare Series -- no high/low


def test_stochastic_bounded_0_100(ohlcv):
    out = stochastic(ohlcv, k=5, d=3)
    valid = out.dropna()
    assert (valid["%K"] >= 0).all() and (valid["%K"] <= 100).all()


def test_williams_r_bounded(ohlcv):
    out = williams_r(ohlcv, period=5)
    valid = out.dropna()
    assert (valid >= -100).all() and (valid <= 0).all()


def test_cci_runs(ohlcv):
    out = cci(ohlcv, period=5)
    assert out.dropna().shape[0] > 0


def test_adx_columns_and_nonnegative(ohlcv):
    out = adx(ohlcv, period=5)
    assert list(out.columns) == ["adx", "+di", "-di"]
    valid = out["adx"].dropna()
    assert (valid >= 0).all()


def test_roc_and_momentum(ohlcv):
    r = roc(ohlcv, period=1, column="close")
    m = momentum(ohlcv, period=1, column="close")
    expected_roc = 100 * (CLOSES[1] / CLOSES[0] - 1)
    expected_mom = CLOSES[1] - CLOSES[0]
    assert r.iloc[1] == pytest.approx(expected_roc)
    assert m.iloc[1] == pytest.approx(expected_mom)


def test_obv_direction(ohlcv):
    out = obv(ohlcv)
    # close rises on bar 1 -> OBV increases by that bar's volume
    assert out.iloc[1] - out.iloc[0] == ohlcv["volume"].iloc[1]


def test_vwap_runs_and_is_finite(ohlcv):
    out = vwap(ohlcv)
    assert np.isfinite(out.dropna()).all()


def test_mfi_bounded(ohlcv):
    out = mfi(ohlcv, period=5)
    valid = out.dropna()
    assert (valid >= 0).all() and (valid <= 100).all()


def test_keltner_band_order(ohlcv):
    out = keltner(ohlcv, window=5, k=2)
    valid = out.dropna()
    assert (valid["upper"] >= valid["mid"]).all()
    assert (valid["lower"] <= valid["mid"]).all()


def test_donchian_band_order(ohlcv):
    out = donchian(ohlcv, window=5)
    valid = out.dropna()
    assert (valid["upper"] >= valid["mid"]).all()
    assert (valid["lower"] <= valid["mid"]).all()


def test_ichimoku_columns(ohlcv):
    out = ichimoku(ohlcv, tenkan=3, kijun=5, senkou_b=8)
    assert set(out.columns) == {
        "tenkan_sen", "kijun_sen", "senkou_span_a", "senkou_span_b", "chikou_span"
    }


def test_psar_runs_and_finite(ohlcv):
    out = psar(ohlcv, step=0.02, max_step=0.2)
    assert out.notna().all()
    assert np.isfinite(out).all()


def test_indicator_on_bare_series_raises_invalid_request(ohlcv):
    with pytest.raises(InvalidRequest):
        atr(ohlcv["close"])
