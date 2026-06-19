from __future__ import annotations

import io

import pandas as pd
import requests

from marketkit.config import REQUEST_TIMEOUT, USER_AGENT
from marketkit.errors import SourceError
from marketkit.sources.base import register

_URL = "https://stooq.com/q/d/l/"


class StooqSource:
    name = "stooq"
    requires_key = False

    def fetch(self, ticker, start, end, interval):
        if interval != "1d":
            raise SourceError("stooq supports daily only")
        symbol = ticker.lower()
        if "." not in symbol:
            symbol += ".us"
        params = {
            "s": symbol,
            "i": "d",
            "d1": pd.Timestamp(start).strftime("%Y%m%d"),
            "d2": pd.Timestamp(end).strftime("%Y%m%d"),
        }
        try:
            r = requests.get(
                _URL,
                params=params,
                headers={"User-Agent": USER_AGENT},
                timeout=REQUEST_TIMEOUT,
            )
        except requests.RequestException as e:
            raise SourceError(f"stooq network error: {e}") from e

        if r.status_code != 200 or r.text.strip().startswith("<"):
            raise SourceError(f"stooq failed (HTTP {r.status_code})")
        df = pd.read_csv(io.StringIO(r.text))
        if df.empty or "Date" not in df.columns:
            raise SourceError("stooq returned no usable data")
        df = df.set_index("Date")  # columns: Open/High/Low/Close/Volume
        return df  # raw; clean._RENAME_MAP['stooq'] maps to canonical


register(StooqSource())
