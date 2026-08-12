"""Contract/unit tests for routers._serde._clean_dataframe (WS1a1 membership fix).

Pure-pandas — no sponsor (vnstock_data) import required. Run:
    pip install -r requirements-dev.txt && pytest tests/test_serde.py
"""
import pandas as pd
from routers._serde import _clean_dataframe


def test_none():
    assert _clean_dataframe(None) == []


def test_list_passthrough():
    assert _clean_dataframe([1, 2, 3]) == [1, 2, 3]


def test_dict_wrapped():
    assert _clean_dataframe({"a": 1}) == [{"a": 1}]


def test_empty_dataframe():
    assert _clean_dataframe(pd.DataFrame()) == []


def test_dataframe_records():
    df = pd.DataFrame([{"symbol": "ACB"}, {"symbol": "TCB"}])
    assert _clean_dataframe(df) == [{"symbol": "ACB"}, {"symbol": "TCB"}]


def test_series_named_to_records():
    """THE MEMBERSHIP CONTRACT — was the bug. Listing.symbols_by_group returns a
    named pd.Series; it must serialize to [{symbol: ...}], not vanish to []."""
    s = pd.Series(["ACB", "ANV", "BAF"], name="symbol")
    out = _clean_dataframe(s)
    assert out == [{"symbol": "ACB"}, {"symbol": "ANV"}, {"symbol": "BAF"}]


def test_series_unnamed_to_records():
    # Unnamed Series → single column keyed by 0; must still be non-empty records.
    s = pd.Series(["ACB", "ANV"])
    out = _clean_dataframe(s)
    assert len(out) == 2
    assert out[0] == {0: "ACB"}


def test_series_empty():
    assert _clean_dataframe(pd.Series([], dtype=float, name="symbol")) == []


def test_unknown_type_returns_empty():
    assert _clean_dataframe(42) == []


def test_dataframe_preserves_nan_as_none():
    df = pd.DataFrame([{"a": 1.0, "b": float("nan")}])
    out = _clean_dataframe(df)
    assert out == [{"a": 1.0, "b": None}]
