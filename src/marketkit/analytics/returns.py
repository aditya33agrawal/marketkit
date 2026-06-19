from __future__ import annotations

from typing import Union

import numpy as np
import pandas as pd

PriceData = Union[pd.DataFrame, pd.Series]


def returns(data: PriceData, *, kind: str = "simple", column: str = "adj_close") -> pd.Series:
    px = data[column] if isinstance(data, pd.DataFrame) else data
    if kind == "log":
        return np.log(px / px.shift(1)).dropna()
    return px.pct_change().dropna()


def cagr(data: PriceData, *, periods_per_year: int = 252, column: str = "adj_close") -> float:
    px = data[column] if isinstance(data, pd.DataFrame) else data
    total = px.iloc[-1] / px.iloc[0]
    years = len(px) / periods_per_year
    return float(total ** (1 / years) - 1)
