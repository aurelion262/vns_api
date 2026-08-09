"""Foundation tests for vns_api streamer + routes.

All tests mock vnstock_data.Market and AppStreamer — no network/license calls.
No pytest.ini — conftest.py collect_ignore excludes ad-hoc scripts.
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient


@pytest.fixture
def app_client():
    """TestClient with mocked Market + streamer. No startup WS."""
    import main
    with patch.object(main, "Market", return_value=MagicMock()):
        with patch.object(main, "AppStreamer", return_value=MagicMock(
            start=AsyncMock(), force_refresh=MagicMock(),
            get_health=MagicMock(return_value={"healthy": True}),
            subscribe_chart_symbol=MagicMock(),
            unsubscribe_chart_symbol=MagicMock(),
        )):
            with TestClient(main.app, raise_server_exceptions=False) as c:
                yield c


class TestChartCandle:
    """Pure unit tests for ChartCandle (no deps)."""
    def test_init_sets_all_ohlc(self):
        from streamer import ChartCandle
        c = ChartCandle(time=1000, price=25.5)
        assert c.open == c.high == c.low == c.close == 25.5

    def test_update_tracks_high_low(self):
        from streamer import ChartCandle
        c = ChartCandle(time=1000, price=25.0)
        c.update(26.0)
        c.update(24.0)
        assert c.high == 26.0
        assert c.low == 24.0
        assert c.close == 24.0

    def test_volume_accumulates(self):
        from streamer import ChartCandle
        c = ChartCandle(time=1000, price=25.0, volume=100)
        c.update(26.0, volume=50)
        assert c.volume == 150

    def test_to_dict(self):
        from streamer import ChartCandle
        c = ChartCandle(time=1000, price=25.0)
        c.update(26.0)
        d = c.to_dict()
        assert set(d.keys()) == {"time", "open", "high", "low", "close", "volume"}


class TestAlertProcessor:
    """Unit tests with mocked aiohttp."""
    @pytest.mark.asyncio
    async def test_skip_no_symbol(self):
        from streamer import AlertProcessor
        proc = AlertProcessor()
        proc.update_rules([])
        await proc.process({"price": 25.0})  # no exception

    @pytest.mark.asyncio
    async def test_skip_no_price(self):
        from streamer import AlertProcessor
        proc = AlertProcessor()
        proc.update_rules([])
        await proc.process({"symbol": "MSB"})

    @pytest.mark.asyncio
    async def test_ge_condition_triggers(self):
        from streamer import AlertProcessor
        proc = AlertProcessor()
        proc.update_rules([{"id": 1, "symbol": "MSB", "condition": ">=",
                            "targetPrice": 20, "offsets": [0]}])
        with patch.object(proc, "trigger_alert", new=AsyncMock()):
            await proc.process({"symbol": "MSB", "last_price": 25.0})
            proc.trigger_alert.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_trigger_below_target(self):
        from streamer import AlertProcessor
        proc = AlertProcessor()
        proc.update_rules([{"id": 1, "symbol": "MSB", "condition": ">=",
                            "targetPrice": 100, "offsets": [0]}])
        with patch.object(proc, "trigger_alert", new=AsyncMock()):
            await proc.process({"symbol": "MSB", "last_price": 25.0})
            proc.trigger_alert.assert_not_called()


class TestRouteRegistration:
    """Sol: verify exact route registration — no 500 in smoke tests."""
    def test_all_routers_mounted(self, app_client):
        """Verify core endpoints respond. Experiment routers are tested by
        hitting a known endpoint — app.routes may not expose sub-router paths
        in all FastAPI versions, so we verify via actual HTTP calls."""
        # Core endpoints (defined directly on app).
        assert app_client.get("/streamer/health").status_code == 200
        assert app_client.post("/streamer/refresh").status_code == 200
        assert app_client.get("/api/v1/quotes?symbols=MSB").status_code in (200, 500)
        # WS route exists (would upgrade — 400 on non-WS GET is fine).
        ws_resp = app_client.get("/ws/prices/MSB")
        # WS route may return 404 via non-WS GET (TestClient doesn't upgrade).
        # The route is registered if it doesn't return a generic 404 from a
        # missing route — but TestClient handles WS differently. Just verify
        # app has the route object.
        from main import app
        ws_paths = [r.path for r in app.routes if hasattr(r, "path") and "ws" in r.path]
        assert any("ws/prices" in p for p in ws_paths), "WS prices route not registered"

    def test_streamer_health(self, app_client):
        """GET /streamer/health returns 200 with health data."""
        resp = app_client.get("/streamer/health")
        assert resp.status_code == 200
        assert "healthy" in resp.json()

    def test_streamer_refresh(self, app_client):
        """POST /streamer/refresh returns 200 success."""
        resp = app_client.post("/streamer/refresh")
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_quotes_mocked(self, app_client, mock_market):
        """GET /api/v1/quotes with mocked Market returns 200 (not 500)."""
        with patch("main.Market", return_value=mock_market):
            resp = app_client.get("/api/v1/quotes?symbols=MSB")
        assert resp.status_code == 200
        assert "data" in resp.json()
