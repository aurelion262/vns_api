"""Pytest conftest — keep vns_api tests sponsor-free (no network / no license).

vns_api routers import `vnstock_data` at module load, which triggers device-register
authentication against vnstocks.com. Tests must run fully offline. We pre-seed
sys.modules with MagicMock stubs for every sponsor submodule the routers import,
BEFORE any router module is imported (conftest loads prior to test-module collection).

Effect: `from vnstock_data... import X` resolves to a MagicMock attribute, so the
router imports cleanly with no sponsor side-effects. Tests that need to assert on
an upstream call still patch the name as used by the router (e.g.
`patch("routers.experiment_data_ref.KBSListing")`).

We FORCE the stub (assign, not setdefault) so behaviour is identical whether or not
the real vnstock_data is installed in the venv.
"""
import sys
from unittest.mock import MagicMock

# Every sponsor submodule imported by routers/experiment_data_ref.py (and siblings).
_SPONSOR_MODULES = [
    "vnstock_data",
    "vnstock_data.explorer",
    "vnstock_data.explorer.kbs",
    "vnstock_data.explorer.kbs.company",
    "vnstock_data.explorer.kbs.listing",
    "vnstock_data.explorer.vci",
    "vnstock_data.explorer.vci.company",
]
for _mod in _SPONSOR_MODULES:
    sys.modules[_mod] = MagicMock()
