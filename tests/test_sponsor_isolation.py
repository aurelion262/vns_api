"""Sponsor-isolation regression — IMPL verdict R1 F1 (cả quota + serde branch).

Khóa test boundary: sau khi import `main` (toàn bộ router chain), KHÔNG module
vendor nào (`vnstock*`, `vnai*`) được nạp thật từ site-packages — mọi entry
sys.modules phải là test double do conftest pre-seed (verdict repro: thiếu
`vnstock`, `vnstock.ui`, `vnai`, `vnai.beam`, `vnai.beam.agents` khiến package
thật vẫn load + banner vendor in ra).

Lớp 2 — clean-process: chạy lại đúng seeding conftest + import main trong process
con KHÔNG pytest; khóa đủ 3 tín hiệu verdict: (a) không vendor-real module,
(b) không banner vendor import-time, (c) không artefact bootstrap (AGENTS.md).
"""
import os
import subprocess
import sys


def _real_vendor_modules() -> dict:
    import main  # conftest đã seed trước (pytest); import đủ router chain

    bad = {}
    for name, mod in sys.modules.items():
        if name.startswith(("vnstock", "vnai")) and mod is not None:
            f = getattr(mod, "__file__", None)
            if f and isinstance(f, str) and "site-packages" in f:
                bad[name] = f
    return bad


def test_inprocess_no_real_vendor_module_after_main_import():
    bad = _real_vendor_modules()
    assert not bad, f"vendor thật vẫn được nạp: {bad}"


_CLEAN_IMPORT_SCRIPT = r"""
import sys, os
sys.path.insert(0, os.path.join(os.getcwd(), "tests"))
import conftest  # đúng seeding pytest dùng — MỘT nguồn (tests/conftest.py)
import main
bad = {}
for name, mod in sys.modules.items():
    if name.startswith(("vnstock", "vnai")) and mod is not None:
        f = getattr(mod, "__file__", None)
        if f and isinstance(f, str) and "site-packages" in f:
            bad[name] = f
print("REAL_MODULES:", bad)
print("IMPORT_DONE")
"""


def test_clean_process_no_vendor_banner_or_artifact():
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    agents_md = os.path.join(repo, "AGENTS.md")
    existed = os.path.exists(agents_md)
    r = subprocess.run(
        [sys.executable, "-c", _CLEAN_IMPORT_SCRIPT],
        cwd=repo, capture_output=True, text=True, timeout=180,
    )
    out = (r.stdout or "") + (r.stderr or "")
    assert r.returncode == 0, out
    assert "IMPORT_DONE" in r.stdout, out
    assert "REAL_MODULES: {}" in r.stdout, out
    # banner vendor import-time (version check) không được xuất hiện
    for marker in ("is available", "vnstocks.com/docs", "vnstocks.com/onboard"):
        assert marker not in out, f"banner vendor xuất hiện: {marker!r}"
    # không sinh artefact bootstrap trong repo
    assert existed or not os.path.exists(agents_md), "import main sinh AGENTS.md"
