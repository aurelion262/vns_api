"""Tests for interval forwarding on OHLCV endpoints.

Sol R2: tests must be completely offline — no vnstock license/network.
Strategy: install fake vnstock_data module in sys.modules BEFORE importing
the router, then test router functions directly (NOT via main/TestClient).
Asserts exact downstream kwargs passed to ohlcv().
"""
import sys
import types
from unittest.mock import MagicMock, patch

import pytest


def _install_fake_vnstock_data():
    """Install a fake vnstock_data module so router import doesn't call license."""
    if "vnstock_data" in sys.modules:
        return  # already installed (real or fake)
    fake = types.ModuleType("vnstock_data")
    fake.Market = MagicMock()
    sys.modules["vnstock_data"] = fake


# Install fakes BEFORE any router import.
_install_fake_vnstock_data()


@pytest.fixture
def mock_market():
    """Mock Market with a chainable equity/index/futures → ohlcv."""
    import pandas as pd
    market = MagicMock()
    df = pd.DataFrame([{"date": "2026-01-01", "open": 25, "close": 25.5}])
    market.equity.return_value.ohlcv.return_value = df
    market.index.return_value.ohlcv.return_value = df
    market.futures.return_value.ohlcv.return_value = df
    return market


class TestIntervalForwarding:
    """Verify interval param forwarded to ohlcv() with exact kwargs."""

    def test_equity_interval_1m(self, mock_market):
        """equity ohlcv forwards interval='1m'."""
        from routers.experiment_data_market import equity_ohlcv
        with patch("routers.experiment_data_market.Market", return_value=mock_market):
            equity_ohlcv(symbol="MSB", interval="1m")
        mock_market.equity.return_value.ohlcv.assert_called_once()
        kwargs = mock_market.equity.return_value.ohlcv.call_args[1]  # keyword args
        assert kwargs.get("interval") == "1m"

    def test_index_interval_5m(self, mock_market):
        """index ohlcv forwards interval='5m'."""
        from routers.experiment_data_market import index_ohlcv
        with patch("routers.experiment_data_market.Market", return_value=mock_market):
            index_ohlcv(symbol="VNINDEX", interval="5m")
        mock_market.index.return_value.ohlcv.assert_called_once()
        kwargs = mock_market.index.return_value.ohlcv.call_args[1]
        assert kwargs.get("interval") == "5m"

    def test_futures_interval_15m(self, mock_market):
        """futures ohlcv forwards interval='15m'."""
        from routers.experiment_data_market import futures_ohlcv
        with patch("routers.experiment_data_market.Market", return_value=mock_market):
            futures_ohlcv(symbol="VN30F1M", interval="15m")
        mock_market.futures.return_value.ohlcv.assert_called_once()
        kwargs = mock_market.futures.return_value.ohlcv.call_args[1]
        assert kwargs.get("interval") == "15m"

    def test_equity_default_interval_none(self, mock_market):
        """Without interval param, _parse_kwargs produces interval=None."""
        from routers.experiment_data_market import equity_ohlcv
        with patch("routers.experiment_data_market.Market", return_value=mock_market):
            equity_ohlcv(symbol="MSB")
        kwargs = mock_market.equity.return_value.ohlcv.call_args[1]
        assert kwargs.get("interval") is None
