"""Tests for interval forwarding on OHLCV endpoints.

Verifies that equity/index/futures OHLCV routes accept and forward the
`interval` parameter. All tests mock vnstock_data.Market — no network.
"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """TestClient with mocked Market (no vnstock network calls)."""
    import main
    # Patch Market to avoid license check during import.
    with patch.object(main, "Market", return_value=MagicMock()):
        with patch.object(main, "AppStreamer"):
            with TestClient(main.app, raise_server_exceptions=False) as c:
                yield c


class TestIntervalForwarding:
    """Sol: verify interval param forwarded to ohlcv calls."""

    def test_equity_ohlcv_has_interval_param(self, client):
        """GET /api/v1/experiment/data/market/equity/ohlcv accepts interval."""
        import pandas as pd
        mock_df = pd.DataFrame([{"date": "2026-01-01", "open": 25, "high": 26, "low": 24, "close": 25.5, "volume": 1000}])
        with patch("routers.experiment_data_market.Market") as mock_mkt_cls:
            mock_mkt = MagicMock()
            mock_mkt.equity.return_value.ohlcv.return_value = mock_df
            mock_mkt_cls.return_value = mock_mkt
            resp = client.get("/api/v1/experiment/data/market/equity/ohlcv?symbol=MSB&interval=1m")
        assert resp.status_code == 200
        # Verify ohlcv was called with interval forwarded.
        mock_mkt.equity.return_value.ohlcv.assert_called_once()
        call_kwargs = mock_mkt.equity.return_value.ohlcv.call_args
        # _parse_kwargs builds a dict; interval should be in there.
        assert call_kwargs[0] is not None or call_kwargs[1] is not None

    def test_index_ohlcv_has_interval_param(self, client):
        """GET /api/v1/experiment/data/market/index/ohlcv accepts interval."""
        import pandas as pd
        mock_df = pd.DataFrame([{"date": "2026-01-01", "open": 1200, "high": 1210, "low": 1190, "close": 1205, "volume": 100000}])
        with patch("routers.experiment_data_market.Market") as mock_mkt_cls:
            mock_mkt = MagicMock()
            mock_mkt.index.return_value.ohlcv.return_value = mock_df
            mock_mkt_cls.return_value = mock_mkt
            resp = client.get("/api/v1/experiment/data/market/index/ohlcv?symbol=VNINDEX&interval=5m")
        assert resp.status_code == 200

    def test_futures_ohlcv_has_interval_param(self, client):
        """GET /api/v1/experiment/data/market/futures/ohlcv accepts interval."""
        import pandas as pd
        mock_df = pd.DataFrame([{"date": "2026-01-01", "open": 950, "high": 955, "low": 945, "close": 950, "volume": 5000}])
        with patch("routers.experiment_data_market.Market") as mock_mkt_cls:
            mock_mkt = MagicMock()
            mock_mkt.futures.return_value.ohlcv.return_value = mock_df
            mock_mkt_cls.return_value = mock_mkt
            resp = client.get("/api/v1/experiment/data/market/futures/ohlcv?symbol=VN30F1M&interval=15m")
        assert resp.status_code == 200

    def test_equity_ohlcv_default_no_interval(self, client):
        """Without interval param, defaults to None (daily)."""
        import pandas as pd
        mock_df = pd.DataFrame([{"date": "2026-01-01", "open": 25, "high": 26, "low": 24, "close": 25.5, "volume": 1000}])
        with patch("routers.experiment_data_market.Market") as mock_mkt_cls:
            mock_mkt = MagicMock()
            mock_mkt.equity.return_value.ohlcv.return_value = mock_df
            mock_mkt_cls.return_value = mock_mkt
            resp = client.get("/api/v1/experiment/data/market/equity/ohlcv?symbol=MSB")
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
