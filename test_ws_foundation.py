"""Foundation tests for vns_api streamer + routes.

Sol R2 requirements:
- Fake vnstock_pipeline.stream.WSSClient + vnstock_data BEFORE any import.
- NO pytest-asyncio — use asyncio.run in sync tests.
- NO conftest/pytest.ini/collect_ignore — ad-hoc scripts renamed to manual_*.
- NO HTTP 500 in smoke tests.
- Test ChartProcessor subscriber logic + WS route.
"""
import sys
import types
import asyncio
from unittest.mock import MagicMock, patch

# ============================================================
# Install fake sponsor modules BEFORE importing streamer/main.
# This ensures tests run completely offline — no vnstock license.
# ============================================================
def _install_fakes():
    """Patch sys.modules with fake vnstock_pipeline + vnstock_data."""
    if "vnstock_pipeline" not in sys.modules:
        fake_pipeline = types.ModuleType("vnstock_pipeline")
        fake_stream = types.ModuleType("vnstock_pipeline.stream")
        fake_processors = types.ModuleType("vnstock_pipeline.stream.processors")

        class _FakeDataProcessor:
            """Minimal DataProcessor base for AlertProcessor/ChartProcessor."""
            def __init__(self):
                self.processors = []
            def add_processor(self, p):
                self.processors.append(p)

        class _FakeWSSClient:
            """Mockable WSSClient — no real connection."""
            def __init__(self, *args, **kwargs):
                self.market = "VN"
                self._connected = False
                self._raw_messages = []
                self.session_manager = None
            def connect(self):
                self._connected = True
            def disconnect(self):
                self._connected = False
            def is_connected(self):
                return self._connected
            def add_processor(self, p):
                pass
            def add_raw_message(self, msg):
                self._raw_messages.append(msg)
            def clear_raw_messages(self):
                self._raw_messages = []
            def send_message(self, msg):
                pass

        fake_stream.WSSClient = _FakeWSSClient
        fake_processors.DataProcessor = _FakeDataProcessor
        fake_pipeline.stream = fake_stream
        sys.modules["vnstock_pipeline"] = fake_pipeline
        sys.modules["vnstock_pipeline.stream"] = fake_stream
        sys.modules["vnstock_pipeline.stream.processors"] = fake_processors

    if "vnstock_data" not in sys.modules:
        fake_data = types.ModuleType("vnstock_data")
        # Sol R2: routers import Market, Reference, Analytics, Fundamental,
        # Insights, Macro — all must exist in the fake module.
        for name in ("Market", "Reference", "Analytics", "Fundamental",
                      "Insights", "Macro"):
            setattr(fake_data, name, MagicMock())
        # Must be a package (has __path__) for sub-imports like
        # vnstock_data.explorer.kbs.company to resolve.
        fake_data.__path__ = []
        fake_data.__spec__ = types.SimpleNamespace(submodule_search_locations=[])
        sys.modules["vnstock_data"] = fake_data

        # Fake vnstock_data.explorer submodules (all imports from routers).
        fake_explorer = types.ModuleType("vnstock_data.explorer")
        fake_explorer.__path__ = []
        sys.modules["vnstock_data.explorer"] = fake_explorer

        # kbs subpackage
        fake_kbs = types.ModuleType("vnstock_data.explorer.kbs")
        fake_kbs.__path__ = []
        sys.modules["vnstock_data.explorer.kbs"] = fake_kbs

        for submod in ("company", "listing"):
            m = types.ModuleType(f"vnstock_data.explorer.kbs.{submod}")
            setattr(m, "Company" if submod == "company" else "Listing", MagicMock())
            sys.modules[f"vnstock_data.explorer.kbs.{submod}"] = m

        # vci subpackage
        fake_vci = types.ModuleType("vnstock_data.explorer.vci")
        fake_vci.__path__ = []
        sys.modules["vnstock_data.explorer.vci"] = fake_vci

        fake_vci_co = types.ModuleType("vnstock_data.explorer.vci.company")
        fake_vci_co.Company = MagicMock()
        sys.modules["vnstock_data.explorer.vci.company"] = fake_vci_co

    # Also fake vnstock_ta (real package imports vnstock_data.ui internally).
    if "vnstock_ta" not in sys.modules:
        fake_ta = types.ModuleType("vnstock_ta")
        fake_ta.Indicator = MagicMock()
        fake_ta.Plotter = MagicMock()
        sys.modules["vnstock_ta"] = fake_ta

    # Fake vnstock_data.ui (imported by vnstock_ta internally).
    if "vnstock_data.ui" not in sys.modules:
        fake_ui = types.ModuleType("vnstock_data.ui")
        fake_ui.Market = MagicMock()
        sys.modules["vnstock_data.ui"] = fake_ui

_install_fakes()


# ============================================================
# Tests for ChartCandle (pure unit — no deps)
# ============================================================
class TestChartCandle:
    def test_init(self):
        from streamer import ChartCandle
        c = ChartCandle(time=1000, price=25.5)
        assert c.open == c.high == c.low == c.close == 25.5
        assert c.volume == 0

    def test_update_high_low(self):
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
        d = c.to_dict()
        assert set(d.keys()) == {"time", "open", "high", "low", "close", "volume"}


# ============================================================
# Tests for AlertProcessor (async via asyncio.run, no pytest-asyncio)
# ============================================================
class TestAlertProcessor:
    def test_skip_no_symbol(self):
        from streamer import AlertProcessor
        proc = AlertProcessor()
        proc.update_rules([])
        asyncio.run(proc.process({"price": 25.0}))  # no crash

    def test_skip_no_price(self):
        from streamer import AlertProcessor
        proc = AlertProcessor()
        proc.update_rules([])
        asyncio.run(proc.process({"symbol": "MSB"}))

    def _async_noop(self):
        """Factory for an async noop mock (replaces asyncio.coroutine, removed in 3.12)."""
        async def _noop(*a, **kw):
            pass
        return _noop

    def test_ge_triggers_above(self):
        from streamer import AlertProcessor
        proc = AlertProcessor()
        proc.update_rules([{"id": 1, "symbol": "MSB", "condition": ">=",
                            "targetPrice": 20, "offsets": [0]}])
        with patch.object(proc, "trigger_alert", side_effect=self._async_noop()) as mock_ta:
            asyncio.run(proc.process({"symbol": "MSB", "last_price": 25.0}))
            mock_ta.assert_called_once()

    def test_no_trigger_below_target(self):
        from streamer import AlertProcessor
        proc = AlertProcessor()
        proc.update_rules([{"id": 1, "symbol": "MSB", "condition": ">=",
                            "targetPrice": 100, "offsets": [0]}])
        with patch.object(proc, "trigger_alert", side_effect=self._async_noop()) as mock_ta:
            asyncio.run(proc.process({"symbol": "MSB", "last_price": 25.0}))
            mock_ta.assert_not_called()


# ============================================================
# Tests for ChartProcessor subscriber logic
# ============================================================
class TestChartProcessorSubscribers:
    """Sol R2: subscriber lifecycle tests."""

    def _setup(self):
        from streamer import ChartProcessor
        cp = ChartProcessor()
        return cp

    def test_subscribe_returns_queue(self):
        cp = self._setup()
        q = cp.subscribe("MSB")
        assert isinstance(q, asyncio.Queue)
        assert "MSB" in cp.subscribers

    def test_two_subscribers_same_symbol(self):
        """a) Two subscribers same symbol: both get queues, no seed reset."""
        cp = self._setup()
        q1 = cp.subscribe("MSB")
        q2 = cp.subscribe("MSB")
        assert len(cp.subscribers["MSB"]) == 2
        assert q1 != q2

    def test_unsubscribe_one_keeps_symbol(self):
        """b) Leave one subscriber → symbol still in subscribers dict."""
        cp = self._setup()
        q1 = cp.subscribe("MSB")
        q2 = cp.subscribe("MSB")
        cp.unsubscribe("MSB", q1)
        assert "MSB" in cp.subscribers  # still has q2
        assert len(cp.subscribers["MSB"]) == 1

    def test_unsubscribe_last_removes_symbol(self):
        """c) Leave last subscriber → symbol removed + candle cleared."""
        cp = self._setup()
        q = cp.subscribe("MSB")
        # Simulate a candle being set.
        from streamer import ChartCandle
        cp.candles["MSB"] = ChartCandle(time=1000, price=25.0)
        cp.unsubscribe("MSB", q)
        assert "MSB" not in cp.subscribers
        assert "MSB" not in cp.candles  # cleaned up


# ============================================================
# Tests for AppStreamer chart symbol management
# ============================================================
class TestAppStreamerChartSymbols:
    """Sol R2: chart symbol subscribe/unsubscribe from upstream perspective."""

    def _setup(self):
        from streamer import AppStreamer
        return AppStreamer()

    def test_subscribe_chart_symbol_adds(self):
        s = self._setup()
        s.subscribe_chart_symbol("MSB")
        assert "MSB" in s.chart_symbols

    def test_subscribe_same_symbol_no_dup(self):
        s = self._setup()
        s.subscribe_chart_symbol("MSB")
        s.subscribe_chart_symbol("MSB")
        assert len(s.chart_symbols) == 1

    def test_unsubscribe_chart_symbol_removes(self):
        s = self._setup()
        s.subscribe_chart_symbol("MSB")
        s.unsubscribe_chart_symbol("MSB")
        assert "MSB" not in s.chart_symbols

    def test_unsubscribe_when_alert_still_uses_symbol(self):
        """If alert uses MSB, chart unsubscribe keeps it in upstream union."""
        s = self._setup()
        s.symbols = {"MSB"}  # alert uses MSB
        s.subscribe_chart_symbol("MSB")
        s.unsubscribe_chart_symbol("MSB")
        # chart_symbols empty but symbols still has MSB
        assert "MSB" not in s.chart_symbols
        assert "MSB" in s.symbols


# ============================================================
# Tests for route endpoints (TestClient, mocked streamer)
# ============================================================
class TestRoutes:
    """Smoke tests — no HTTP 500 allowed."""

    def test_streamer_health(self):
        """GET /streamer/health returns 200 with health data."""
        from fastapi.testclient import TestClient
        with patch("main.Market", return_value=MagicMock()):
            import main
            # Patch the global streamer instance (created at module level).
            main.streamer.get_health = MagicMock(return_value={"healthy": True})
            main.streamer.force_refresh = MagicMock()
            with TestClient(main.app) as client:
                resp = client.get("/streamer/health")
        assert resp.status_code == 200
        assert resp.json()["healthy"] is True

    def test_streamer_refresh(self):
        from fastapi.testclient import TestClient
        mock_streamer = MagicMock()
        mock_streamer.force_refresh.return_value = None
        mock_streamer.start = MagicMock()
        with patch("main.AppStreamer", return_value=mock_streamer):
            with patch("main.Market", return_value=MagicMock()):
                from main import app
                with TestClient(app) as client:
                    resp = client.post("/streamer/refresh")
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_quotes_mocked(self):
        """GET /api/v1/quotes with mocked Market returns 200 (not 500)."""
        import pandas as pd
        from fastapi.testclient import TestClient
        mock_market = MagicMock()
        mock_market.quote.return_value = pd.DataFrame(
            [{"symbol": "MSB", "lastPrice": 25.5}])
        mock_streamer = MagicMock()
        mock_streamer.start = MagicMock()
        with patch("main.AppStreamer", return_value=mock_streamer):
            with patch("main.Market", return_value=mock_market):
                from main import app
                with TestClient(app) as client:
                    resp = client.get("/api/v1/quotes?symbols=MSB")
        assert resp.status_code == 200
        assert "data" in resp.json()

    def test_ws_route_registered(self):
        """WS prices route is registered on app."""
        from streamer import AppStreamer  # verify import works
        mock_streamer = MagicMock()
        mock_streamer.start = MagicMock()
        with patch("main.AppStreamer", return_value=mock_streamer):
            with patch("main.Market", return_value=MagicMock()):
                from main import app
                ws_paths = [r.path for r in app.routes
                            if hasattr(r, "path") and "ws" in r.path]
                assert any("/ws/prices/" in p for p in ws_paths), \
                    "WS prices route not registered"
