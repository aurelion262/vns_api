"""Route-level contract test for /equity/list_by_group (WS1a1 membership, Sol R2).

Mock upstream KBSListing.symbols_by_group → known pd.Series; assert:
  - the route forwards group.upper() == "VN30" to the upstream;
  - exact HTTP response shape {"data":[{"symbol":"ACB"},{"symbol":"TCB"}]}.

Local test harness (vns_api CI does not run pytest; see requirements-dev.txt).
Importing routers.experiment_data_ref triggers the sponsor (vnstock_data) import —
that is expected in the local .venv; the upstream itself is mocked per-test.
"""
import pandas as pd
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers.experiment_data_ref import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def test_list_by_group_vn30_forwards_uppercased_and_serializes_series():
    """Upstream returns a named pd.Series; route serializes to {data:[{symbol}]}
    and forwards group.upper() == 'VN30' to the upstream call."""
    with patch("routers.experiment_data_ref.KBSListing") as MockListing:
        instance = MockListing.return_value
        instance.symbols_by_group.return_value = pd.Series(
            ["ACB", "TCB"], name="symbol"
        )
        r = client.get(
            "/api/v1/experiment/data/reference/equity/list_by_group?group=vn30"
        )
        # exact response contract
        assert r.status_code == 200
        assert r.json() == {"data": [{"symbol": "ACB"}, {"symbol": "TCB"}]}
        # upstream received the upper-cased group
        instance.symbols_by_group.assert_called_once_with("VN30")


def test_list_by_group_empty_series_returns_empty_data_not_500():
    """An empty upstream Series must yield {data:[]} (not crash / not 500)."""
    with patch("routers.experiment_data_ref.KBSListing") as MockListing:
        MockListing.return_value.symbols_by_group.return_value = pd.Series(
            [], dtype=float, name="symbol"
        )
        r = client.get(
            "/api/v1/experiment/data/reference/equity/list_by_group?group=VN100"
        )
        assert r.status_code == 200
        assert r.json() == {"data": []}


def test_list_by_group_upstream_error_propagates_500():
    """If the upstream raises, the route must surface a 500 (not silently empty)."""
    with patch("routers.experiment_data_ref.KBSListing") as MockListing:
        MockListing.return_value.symbols_by_group.side_effect = RuntimeError("boom")
        r = client.get(
            "/api/v1/experiment/data/reference/equity/list_by_group?group=VN30"
        )
        assert r.status_code == 500
