import pytest
import responses

from marketkit.errors import RateLimited, SourceError
from marketkit.sources.stooq import StooqSource
from marketkit.sources.yahoo import YahooSource

YAHOO_URL = "https://query1.finance.yahoo.com/v8/finance/chart/AAPL"
STOOQ_URL = "https://stooq.com/q/d/l/"


def _yahoo_payload(timestamps, closes):
    return {
        "chart": {
            "result": [
                {
                    "timestamp": timestamps,
                    "indicators": {
                        "quote": [
                            {
                                "open": closes,
                                "high": closes,
                                "low": closes,
                                "close": closes,
                                "volume": [100] * len(closes),
                            }
                        ],
                        "adjclose": [{"adjclose": closes}],
                    },
                }
            ],
            "error": None,
        }
    }


@responses.activate
def test_yahoo_fetch_returns_raw_frame():
    ts = [1704240000, 1704326400]  # 2024-01-03, 2024-01-04 (UTC)
    payload = _yahoo_payload(ts, [10.0, 11.0])
    responses.add(responses.GET, YAHOO_URL, json=payload, status=200)

    df = YahooSource().fetch("AAPL", "2024-01-01", "2024-01-05", "1d")
    assert len(df) == 2
    assert list(df["close"]) == [10.0, 11.0]


@responses.activate
def test_yahoo_fetch_raises_rate_limited_on_429():
    responses.add(responses.GET, YAHOO_URL, status=429)
    with pytest.raises(RateLimited):
        YahooSource().fetch("AAPL", "2024-01-01", "2024-01-05", "1d")


@responses.activate
def test_yahoo_fetch_raises_source_error_on_bad_status():
    responses.add(responses.GET, YAHOO_URL, status=500)
    with pytest.raises(SourceError):
        YahooSource().fetch("AAPL", "2024-01-01", "2024-01-05", "1d")


@responses.activate
def test_yahoo_fetch_raises_source_error_on_empty_result():
    responses.add(
        responses.GET, YAHOO_URL, json={"chart": {"result": [], "error": None}}, status=200
    )
    with pytest.raises(SourceError):
        YahooSource().fetch("AAPL", "2024-01-01", "2024-01-05", "1d")


@responses.activate
def test_stooq_fetch_returns_raw_frame():
    csv = "Date,Open,High,Low,Close,Volume\n2024-01-02,1.0,1.5,0.5,1.2,100\n2024-01-03,2.0,2.5,1.5,2.2,200\n"
    responses.add(responses.GET, STOOQ_URL, body=csv, status=200)

    df = StooqSource().fetch("AAPL", "2024-01-01", "2024-01-05", "1d")
    assert len(df) == 2
    assert list(df["Close"]) == [1.2, 2.2]


@responses.activate
def test_stooq_fetch_rejects_intraday():
    with pytest.raises(SourceError):
        StooqSource().fetch("AAPL", "2024-01-01", "2024-01-05", "1h")


@responses.activate
def test_stooq_fetch_raises_on_html_error_page():
    responses.add(responses.GET, STOOQ_URL, body="<html>not found</html>", status=200)
    with pytest.raises(SourceError):
        StooqSource().fetch("AAPL", "2024-01-01", "2024-01-05", "1d")
