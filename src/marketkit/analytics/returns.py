from __future__ import annotations

import numpy as np
import pandas as pd


def returns(data, *, kind="simple", column="adj_close"):
    px = data[column] if isinstance(data, pd.DataFrame) else data
    if kind == "log":
        return np.log(px / px.shift(1)).dropna()
    return px.pct_change().dropna()


def cagr(data, *, periods_per_year=252, column="adj_close"):
    px = data[column] if isinstance(data, pd.DataFrame) else data
    total = px.iloc[-1] / px.iloc[0]
    years = len(px) / periods_per_year
    return total ** (1 / years) - 1
