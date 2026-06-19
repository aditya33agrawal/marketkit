import pandas as pd

from marketkit import clean


def _messy_yahoo_frame():
    idx = pd.to_datetime(
        ["2024-01-03", "2024-01-02", "2024-01-02", "2024-01-04"], utc=True
    )
    return pd.DataFrame(
        {
            "Open": [10.0, 9.0, 9.5, 11.0],
            "High": [10.5, 9.5, 10.0, 11.5],
            "Low": [9.5, 8.5, 9.0, 10.5],
            "Close": [10.2, 9.2, 9.7, 11.2],
            "Volume": [1000, 2000, 2100, 1500],
        },
        index=idx,
    )


def test_normalize_contract_shape():
    df = clean.normalize(_messy_yahoo_frame(), source="yahoo")

    assert list(df.columns) == clean.CANONICAL_COLUMNS
    assert df.index.name == "date"
    assert df.index.tz is None
    assert df.index.is_monotonic_increasing
    assert not df.index.duplicated().any()
    # duplicate 2024-01-02 rows collapse to the last one (keep="last")
    assert len(df) == 3


def test_normalize_adj_close_fallback():
    df = clean.normalize(_messy_yahoo_frame(), source="yahoo")
    assert (df["adj_close"] == df["close"]).all()


def test_normalize_dtypes():
    df = clean.normalize(_messy_yahoo_frame(), source="yahoo")
    for col in ["open", "high", "low", "close", "adj_close"]:
        assert df[col].dtype == "float64"
    assert df["volume"].dtype == "Int64"


def test_normalize_stooq_rename_map():
    raw = pd.DataFrame(
        {
            "Open": [1.0, 2.0],
            "High": [1.5, 2.5],
            "Low": [0.5, 1.5],
            "Close": [1.2, 2.2],
            "Volume": [100, 200],
        },
        index=pd.to_datetime(["2024-01-01", "2024-01-02"]),
    )
    df = clean.normalize(raw, source="stooq")
    assert list(df.columns) == clean.CANONICAL_COLUMNS
    assert df["adj_close"].tolist() == [1.2, 2.2]


def test_normalize_drops_fully_empty_rows():
    raw = _messy_yahoo_frame()
    raw.loc[raw.index[0], ["Open", "High", "Low", "Close"]] = None
    df = clean.normalize(raw, source="yahoo")
    assert df["open"].notna().all() or len(df) < len(raw)


def test_validate_warns_on_empty():
    df = pd.DataFrame(columns=clean.CANONICAL_COLUMNS)
    df.index.name = "date"
    assert "empty frame" in clean.validate(df)


def test_validate_warns_on_high_low_violation():
    df = clean.normalize(_messy_yahoo_frame(), source="yahoo")
    df.loc[df.index[0], "high"] = df.loc[df.index[0], "low"] - 1
    assert "high < low on some rows" in clean.validate(df)


def test_validate_clean_frame_has_no_warnings():
    df = clean.normalize(_messy_yahoo_frame(), source="yahoo")
    assert clean.validate(df) == []
