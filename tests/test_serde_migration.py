"""Serde migration tests — VNSAPI-SERDE-MIGRATION-001 (plan R2 fd7a7b46…).

Lớp 1 — Series RED→GREEN 7/7: mọi router sau migration phải serialize pd.Series
thành records (qua _serde) thay vì nuốt thành [] (tech-spec debt #6 latent bug).
Lớp 2 — Identity-lock 6 router A/B: `_clean_dataframe is routers._serde._clean_dataframe`
(chống tái sinh bản sao private copy-paste).
Lớp 3 — TA exact-legacy matrix T1–T6: expected hard-code từ legacy
`git show 93c8552:routers/experiment_ta.py` (chạy 1 lần khi viết test —
script trong implementation packet); T5 = cross-product repro verdict R1 F1
khóa key `time` (không `time_`); T3/T6 khóa residual unnamed-DatetimeIndex.
Lớp 4 — Route integration stub (macro, nhóm A): sponsor stub trả Series →
HTTP 200 {"data": [records]}.
"""
import importlib

import pandas as pd
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch

from routers import _serde

# 7 router mang bản sao private (khảo sát plan R1 §2)
ROUTER_MODULES = [
    "routers.experiment_data_retail",
    "routers.experiment_data_macro",
    "routers.experiment_data_insights",
    "routers.experiment_data_analytics",
    "routers.experiment_data_market",
    "routers.experiment_data_fun",
    "routers.experiment_ta",
]
# 6 router nhóm A/B phải dùng CHUNG object hàm của _serde (không có wrapper)
IDENTITY_MODULES = [m for m in ROUTER_MODULES if m != "routers.experiment_ta"]

SERIES_IN = pd.Series(["ACB", "VCB"], name="symbol")
SERIES_EXPECTED = [{"symbol": "ACB"}, {"symbol": "VCB"}]


def test_series_serialized_on_all_seven_routers():
    for mod_name in ROUTER_MODULES:
        mod = importlib.import_module(mod_name)
        got = mod._clean_dataframe(SERIES_IN)
        assert got == SERIES_EXPECTED, f"{mod_name}: Series bị nuốt hoặc sai shape: {got!r}"


def test_identity_six_routers_share_serde_function():
    for mod_name in IDENTITY_MODULES:
        mod = importlib.import_module(mod_name)
        assert mod._clean_dataframe is _serde._clean_dataframe, (
            f"{mod_name} còn bản sao private (không dùng chung _serde)"
        )


# --- TA exact-legacy matrix (expected sinh từ legacy @93c8552) ---

_dates = pd.to_datetime(["2026-09-01", "2026-09-02"])


def _flat():
    return pd.DataFrame({"px": [10.0, 11.0], "vol": [100, 200]})


def _multi():
    return pd.DataFrame({("px", "close"): [10.0, 11.0], ("vol", ""): [100, 200]})


TA_MATRIX = [
    # (label, fixture, legacy expected — git show 93c8552:routers/experiment_ta.py)
    ("T1_flat_range", _flat(),
     [{"px": 10.0, "vol": 100}, {"px": 11.0, "vol": 200}]),
    ("T2_flat_namedtime", _flat().set_index(pd.DatetimeIndex(_dates, name="time")),
     [{"time": "2026-09-01", "px": 10.0, "vol": 100},
      {"time": "2026-09-02", "px": 11.0, "vol": 200}]),
    ("T3_flat_unnamedDT", _flat().set_index(pd.DatetimeIndex(_dates)),
     [{"index": pd.Timestamp("2026-09-01 00:00:00"), "px": 10.0, "vol": 100},
      {"index": pd.Timestamp("2026-09-02 00:00:00"), "px": 11.0, "vol": 200}]),
    ("T4_multi_range", _multi(),
     [{"px_close": 10.0, "vol_": 100}, {"px_close": 11.0, "vol_": 200}]),
    # T5 = repro verdict R1 F1: flatten MultiIndex TRƯỚC rồi reset time — key `time`, KHÔNG `time_`
    ("T5_multi_namedtime", _multi().set_index(pd.DatetimeIndex(_dates, name="time")),
     [{"time": "2026-09-01", "px_close": 10.0, "vol_": 100},
      {"time": "2026-09-02", "px_close": 11.0, "vol_": 200}]),
    ("T6_multi_unnamedDT", _multi().set_index(pd.DatetimeIndex(_dates)),
     [{"index": pd.Timestamp("2026-09-01 00:00:00"), "px_close": 10.0, "vol_": 100},
      {"index": pd.Timestamp("2026-09-02 00:00:00"), "px_close": 11.0, "vol_": 200}]),
]


def test_ta_matrix_exact_legacy():
    from routers import experiment_ta
    for label, fixture, expected in TA_MATRIX:
        got = experiment_ta._clean_dataframe(fixture)
        assert got == expected, f"{label}: lệch legacy\n  got:      {got!r}\n  expected: {expected!r}"


def test_ta_matrix_t5_key_is_time_not_time_():
    from routers import experiment_ta
    records = experiment_ta._clean_dataframe(TA_MATRIX[4][1])
    keys = set().union(*(r.keys() for r in records))
    assert "time" in keys and "time_" not in keys, f"keys={keys}"


# --- Route integration (nhóm A — macro): Series qua route thật ---

def test_macro_route_serializes_series():
    from routers.experiment_data_macro import router
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    with patch("routers.experiment_data_macro.Macro") as MockMacro:
        MockMacro.return_value.economy.return_value.gdp.return_value = pd.Series(
            ["+0.5%"], name="gdp_yoy"
        )
        r = client.get("/api/v1/experiment/data/macro/economy/gdp")
        assert r.status_code == 200
        assert r.json() == {"data": [{"gdp_yoy": "+0.5%"}]}
