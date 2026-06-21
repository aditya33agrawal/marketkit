import pandas as pd
import pytest

from marketkit.signals import (
    crossover, crossunder, death_cross, golden_cross, rsi_overbought, rsi_oversold,
)


def test_crossover_detects_upward_cross():
    idx = pd.date_range("2024-01-01", periods=5)
    a = pd.Series([1, 1, 3, 3, 1], index=idx, dtype="float64")
    b = pd.Series([2, 2, 2, 2, 2], index=idx, dtype="float64")
    out = crossover(a, b)
    assert list(out) == [False, False, True, False, False]


def test_crossunder_detects_downward_cross():
    idx = pd.date_range("2024-01-01", periods=5)
    a = pd.Series([3, 3, 1, 1, 3], index=idx, dtype="float64")
    b = pd.Series([2, 2, 2, 2, 2], index=idx, dtype="float64")
    out = crossunder(a, b)
    assert list(out) == [False, False, True, False, False]


@pytest.fixture
def trending_df():
    idx = pd.date_range("2024-01-01", periods=60)
    # a clear regime shift: flat, then a strong rally -- guarantees a golden cross
    closes = [100] * 30 + [100 + i * 3 for i in range(30)]
    return pd.DataFrame({"close": closes}, index=idx)


def test_golden_cross_fires_on_rally(trending_df):
    out = golden_cross(trending_df, fast=5, slow=20)
    assert out.any()


@pytest.fixture
def declining_df():
    idx = pd.date_range("2024-01-01", periods=60)
    closes = [200] * 30 + [200 - i * 3 for i in range(30)]
    return pd.DataFrame({"close": closes}, index=idx)


def test_death_cross_fires_on_decline(declining_df):
    out = death_cross(declining_df, fast=5, slow=20)
    assert out.any()


def test_rsi_oversold_and_overbought_are_mutually_exclusive(trending_df):
    oversold = rsi_oversold(trending_df)
    overbought = rsi_overbought(trending_df)
    both = oversold.fillna(False) & overbought.fillna(False)
    assert not both.any()
