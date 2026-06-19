from __future__ import annotations

import pandas as pd
import requests

from marketkit.config import REQUEST_TIMEOUT, USER_AGENT
from marketkit.errors import RateLimited, SourceError
from marketkit.sources.base import register

_BASE = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"


class YahooSource:
    name = "yahoo"
    requires_key = False

    def fetch(self, ticker, start, end, interval):
        params = {
            "period1": int(pd.Timestamp(start).timestamp()),
            "period2": int(pd.Timestamp(end).timestamp()),
            "interval": interval,
            "events": "div,splits",
            "includeAdjustedClose": "true",
        }
        try:
            r = requests.get(
                _BASE.format(ticker=ticker),
                params=params,
                headers={"User-Agent": USER_AGENT},
                timeout=REQUEST_TIMEOUT,
            )
        except requests.RequestException as e:
            raise SourceError(f"yahoo network error: {e}") from e

        if r.status_code in (401, 429):
            raise RateLimited(f"yahoo throttled (HTTP {r.status_code})")
        if r.status_code != 200:
            raise SourceError(f"yahoo HTTP {r.status_code}")

        try:
            payload = r.json()
        except ValueError as e:
            raise SourceError(f"yahoo returned invalid JSON: {e}") from e

        chart = payload.get("chart", {})
        if chart.get("error"):
            raise SourceError(f"yahoo error: {chart['error']}")
        result = chart.get("result")
        if not result:
            raise SourceError("yahoo returned no result")

        res = result[0]
        ts = res.get("timestamp")
        if not ts:
            raise SourceError("yahoo returned no timestamps")
        q = res["indicators"]["quote"][0]
        adj = res["indicators"].get("adjclose", [{}])[0].get("adjclose")

        df = pd.DataFrame(
            {
                "open": q["open"],
                "high": q["high"],
                "low": q["low"],
                "close": q["close"],
                "volume": q["volume"],
                "adj_close": adj if adj is not None else q["close"],
            },
            index=pd.to_datetime(ts, unit="s"),
        )
        return df  # raw; engine normalizes


register(YahooSource())
