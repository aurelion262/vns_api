"""Pytest config + shared fixtures for vns_api tests.

Sol: collection must be completely offline — no vnstock license/network calls.
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

import pytest

# Ensure vns_api root is importable.
VNS_ROOT = Path(__file__).parent
if str(VNS_ROOT) not in sys.path:
    sys.path.insert(0, str(VNS_ROOT))

# Sol: exclude ad-hoc print() scripts from collection (NOT via pytest.ini).
collect_ignore = ["test_kbs.py", "test_vci.py", "scratch.py"]


@pytest.fixture
def mock_market():
    """Mock vnstock_data.Market — no network calls."""
    mock = MagicMock()
    import pandas as pd
    mock.quote.return_value = pd.DataFrame([
        {"symbol": "MSB", "lastPrice": 25.5, "referencePrice": 25.0},
    ])
    return mock
