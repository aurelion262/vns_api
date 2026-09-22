"""VNSTOCK-328 R2 — contract tests endpoint Fundamental (P1-1, P1-2 verdict Codex 2191d4c).

Khóa contract public với FE (st0nks_web/src/lib/vasAdapter.ts, verify 24/8):
  - Statement endpoints default (KHÔNG query `format`) → wide STABLE: mỗi dòng
    {id, name, level?, order?, unit?, '2018' | '2018-Q1', ...}; FE PERIOD_COL_RE
    /^20\\d{2}(-Q[1-4])?$/ phải bắt được ≥2 cột kỳ (buildIncomeMatrix không null).
  - Output PHẢI GIỐNG HỆT NHAU khi vendor trả long 3.2.8 (id/name/order) hay
    long 3.2.9 (item_id/item/display_order) — contract độc lập version vendor.
  - ratio: long với keys ổn định id/name (FE đọc r.id).
  - Guard order (P1-2): subprocess import main với fake vendor tạo sentinel nếu
    vendor bị import khi guard chưa áp.
"""
import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pandas as pd
import pytest

pytest.importorskip('vnstock_data')  # main.py import vendor — không có sponsor thì skip contract app

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402

client = TestClient(app)

# Mirror PERIOD_COL_RE từ st0nks_web/src/lib/vasAdapter.ts (golden FE)
import re

PERIOD_COL_RE = re.compile(r'^20\d{2}(-Q[1-4])?$')

YEARS = ['2023', '2024', '2025']
QUARTERS = ['2025-Q1', '2025-Q2', '2025-Q3', '2026-Q1']


def _long_df(schema: str, periods, with_meta: bool = True) -> pd.DataFrame:
    """Long fixture: schema 'v328' (id/name/order) hoặc 'v329' (item_id/item/display_order)."""
    ids = ['IS_NET_REVENUE', 'IS_NET_PROFIT_AFTER_TAX', 'IS_BASIC_EARNINGS_PER_SHARE']
    vals = {'IS_NET_REVENUE': 1000.0, 'IS_NET_PROFIT_AFTER_TAX': 100.0, 'IS_BASIC_EARNINGS_PER_SHARE': 10.0}
    rows = []
    for rid in ids:
        for i, p in enumerate(periods):
            row = {'period': p}
            if schema == 'v328':
                row.update({'id': rid, 'name': rid.title(), 'order': 1, 'level': 1, 'unit': 'VNĐ'})
            else:
                row.update({'item_id': rid, 'item': rid.title(), 'display_order': 1, 'level': 1, 'unit': 'VNĐ'})
            row['value'] = vals[rid] * (i + 1)
            rows.append(row)
    return pd.DataFrame(rows)


class _FakeFinance:
    """Thay Finance trong vnstock_data.api.financial (from-import đọc attr lúc gọi)."""
    df_holder = {}
    last_init = None

    def __init__(self, symbol=None, source=None, period=None, **kw):
        type(self).last_init = {'symbol': symbol, 'source': source, 'period': period}

    def income_statement(self, lang='vi', **kw):
        assert 'format' not in kw, f"endpoint phải gọi vendor không format, nhận {kw.get('format')}"
        return type(self).df_holder['df']

    balance_sheet = income_statement
    cash_flow = income_statement

    def ratio(self, lang='vi', **kw):
        return type(self).df_holder['df']


@pytest.fixture
def fake_fundamental(monkeypatch):
    import routers.experiment_data_fun as mod
    monkeypatch.setattr(mod, 'Finance', _FakeFinance)
    _FakeFinance.df_holder = {}
    return _FakeFinance


def _fe_usecols(rows):
    """Golden mirror buildIncomeMatrix: trả list cột kỳ FE sẽ dùng; [] == matrix null."""
    colset = set()
    for r in rows[:3]:
        for k in r.keys():
            if PERIOD_COL_RE.match(k):
                colset.add(k)
    years = sorted(c for c in colset if '-Q' not in c)
    quarters = sorted(c for c in colset if '-Q' in c)
    use = years if len(years) >= 2 else quarters
    return use[-6:]


@pytest.mark.parametrize('schema', ['v328', 'v329'])
def test_income_default_request_is_stable_wide(fake_fundamental, schema):
    """Request KHÔNG có `format` (như FE stockProfile.ts) → wide stable, FE matrix không null.
    R4 F1: wide giờ lọc period theo LOẠI request — request year chỉ trả cột year,
    request quarter (period_type=2) chỉ trả cột quarter (cross-type không lẫn)."""
    _FakeFinance.df_holder['df'] = _long_df(schema, YEARS + QUARTERS)
    # limit=7 giữ đủ kỳ hợp lệ của loại (default limit=4 giờ có hiệu lực F2)
    r = client.get('/api/v1/experiment/data/fun/equity/income_statement',
                   params={'symbol': 'VNM', 'limit': 7})
    assert r.status_code == 200, r.text
    rows = r.json()['data']
    assert rows and 'id' in rows[0] and 'item' in rows[0]  # F3: golden wide = item
    usecols = _fe_usecols(rows)
    assert len(usecols) >= 2, f'FE buildIncomeMatrix sẽ trả null: rows[0] keys={list(rows[0].keys())[:8]}'
    by_id = {row['id']: row for row in rows}
    assert by_id['IS_NET_REVENUE']['2025'] == 3000.0  # 1000 * index 3 (0-based trong YEARS)
    assert all('-Q' not in k for k in rows[0] if PERIOD_COL_RE.match(k))  # year request: chỉ year
    # Quarter qua request period_type=2 — giá trị index 6 trong YEARS+QUARTERS
    r2 = client.get('/api/v1/experiment/data/fun/equity/income_statement',
                    params={'symbol': 'VNM', 'limit': 7, 'period_type': 2})
    assert r2.status_code == 200
    rows2 = r2.json()['data']
    by_id2 = {row['id']: row for row in rows2}
    assert by_id2['IS_BASIC_EARNINGS_PER_SHARE']['2026-Q1'] == 70.0  # 10 * index 6
    assert all('-Q' in k or not PERIOD_COL_RE.match(k) for k in rows2[0])


def test_income_contract_identical_across_vendor_versions(fake_fundamental):
    """Cùng fixture dữ liệu, keys 3.2.8 vs 3.2.9 → response JSON GIỐNG HỆT (contract ổn định)."""
    out = {}
    for schema in ('v328', 'v329'):
        _FakeFinance.df_holder['df'] = _long_df(schema, YEARS + QUARTERS)
        r = client.get('/api/v1/experiment/data/fun/equity/income_statement', params={'symbol': 'VNM'})
        assert r.status_code == 200
        out[schema] = json.dumps(r.json()['data'], sort_keys=True)
    assert out['v328'] == out['v329']


@pytest.mark.parametrize('endpoint', ['balance_sheet', 'cash_flow'])
def test_other_statements_default_wide(fake_fundamental, endpoint):
    # R4 F1: fixture quarter → request phải đồng bộ period_type=2 (wide lọc theo loại)
    _FakeFinance.df_holder['df'] = _long_df('v329', QUARTERS)
    r = client.get(f'/api/v1/experiment/data/fun/equity/{endpoint}',
                   params={'symbol': 'VNM', 'period_type': 2})
    assert r.status_code == 200
    rows = r.json()['data']
    assert 'id' in rows[0]
    assert len(_fe_usecols(rows)) >= 2


def test_format_long_opt_in(fake_fundamental):
    _FakeFinance.df_holder['df'] = _long_df('v329', YEARS)
    r = client.get('/api/v1/experiment/data/fun/equity/income_statement',
                   params={'symbol': 'VNM', 'format': 'long'})
    assert r.status_code == 200
    rows = r.json()['data']
    assert 'period' in rows[0] and 'id' in rows[0] and 'name' in rows[0]  # long giữ id/name


def test_ratio_long_keys_stable(fake_fundamental):
    """FE vasAdapter đọc ratio long theo r.id — 3.2.9 (item_id) phải normalize về id.
    R4 F1: fixture quarter → period_type=2 đồng bộ (lọc theo loại)."""
    _FakeFinance.df_holder['df'] = _long_df('v329', ['2025-Q1', '2025-Q2'])
    r = client.get('/api/v1/experiment/data/fun/equity/ratio',
                   params={'symbol': 'VNM', 'period_type': 2})
    assert r.status_code == 200
    rows = r.json()['data']
    assert 'id' in rows[0] and 'name' in rows[0] and 'period' in rows[0]


def test_identical_duplicate_deduped(fake_fundamental):
    df = pd.concat([_long_df('v329', YEARS), _long_df('v329', YEARS)], ignore_index=True)  # dup toàn bộ
    _FakeFinance.df_holder['df'] = df
    r = client.get('/api/v1/experiment/data/fun/equity/income_statement', params={'symbol': 'VNM'})
    assert r.status_code == 200
    rows = r.json()['data']
    assert len([x for x in rows if x['id'] == 'IS_NET_REVENUE']) == 1


def test_conflicting_duplicate_ambiguous_metric(fake_fundamental):
    df = _long_df('v329', YEARS)
    conflict = df.iloc[[0]].copy()
    conflict['value'] = 999999.0
    _FakeFinance.df_holder['df'] = pd.concat([df, conflict], ignore_index=True)
    r = client.get('/api/v1/experiment/data/fun/equity/income_statement', params={'symbol': 'VNM'})
    assert r.status_code == 500
    assert 'ambiguous_metric' in r.json()['detail']


# ---------------------------------------------------------------- P1-2 guard order

def test_guard_runs_before_vendor_import(tmp_path):
    """Subprocess: fake vendor (shadow vendor thật qua sys.path) tạo sentinel nếu
    lúc import vendor mà guard chưa áp. Không dựa vào machine usercustomize,
    không pre-seed vendor no-op (P1-2 required)."""
    pytest.importorskip('vnai')
    fake_pkg = tmp_path / 'fake_vendor'
    (fake_pkg / 'vnstock_data').mkdir(parents=True)
    (fake_pkg / 'vnstock_data' / '__init__.py').write_text(textwrap.dedent('''
        import os, pathlib, sys, importlib.abc, importlib.machinery
        from unittest.mock import MagicMock

        def _check_guard():
            try:
                import guard_vnstock
                if not guard_vnstock.is_vnai_guard_active():
                    pathlib.Path(os.environ['VN_GUARD_SENTINEL']).write_text(
                        'vendor imported before guard')
            except ImportError:
                pass  # guard_vnstock/vnai không khả dụng — không kết luận được

        _check_guard()  # lúc package vendor được import — guard phải đã áp

        class _SubLoader(importlib.abc.Loader):
            def create_module(self, spec):
                return MagicMock(__name__=spec.name, __path__=[])

            def exec_module(self, module):
                pass

        class _VendorFinder(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if fullname.startswith('vnstock_data.'):
                    return importlib.machinery.ModuleSpec(fullname, _SubLoader(), is_package=True)
                return None

        sys.meta_path.insert(0, _VendorFinder())

        def _pkg_getattr(name):
            return MagicMock()
    '''), encoding='utf-8')
    sentinel = tmp_path / 'sentinel.flag'
    env = {**os.environ,
           'PYTHONPATH': str(fake_pkg) + os.pathsep + str(REPO),
           'VN_GUARD_SENTINEL': str(sentinel)}
    proc = subprocess.run([sys.executable, '-c', 'import main'], env=env,
                          cwd=str(tmp_path), timeout=120, capture_output=True)
    assert proc.returncode == 0, proc.stderr.decode(errors='replace')[-800:]
    assert not sentinel.exists(), 'vendor bị import TRƯỚC khi guard áp (P1-2 regression)'
    # bonus: không file chỉ dẫn nào rơi vào cwd
    assert not (tmp_path / 'AGENTS.md').exists()


def test_conflict_on_non_target_id_is_deterministic(fake_fundamental):
    """P2-2 verdict: duplicate conflicting ở NON-target id là bình thường
    (live 3.2.9 có sẵn) — endpoint vẫn 200, giá trị deterministic (dòng đầu)."""
    df = _long_df('v329', YEARS)
    from routers.experiment_data_fun import _normalize_long_columns
    ndf = _normalize_long_columns(df.copy())  # keys id/name — tránh cột id+item_id song song
    row_a = ndf.iloc[[0]].copy()
    row_a['id'] = 'IS_FINANCIAL_EXPENSES'  # non-target
    row_a['name'] = 'Chi phí tài chính'
    row_a['value'] = 999999.0
    row_b = row_a.copy()
    row_b['value'] = 888888.0  # xung đột THẬT ở non-target id
    fake_fundamental.df_holder['df'] = pd.concat([ndf, row_a, row_b], ignore_index=True)
    r = client.get('/api/v1/experiment/data/fun/equity/income_statement', params={'symbol': 'VNM'})
    assert r.status_code == 200
    rows = r.json()['data']
    fin = [x for x in rows if x['id'] == 'IS_FINANCIAL_EXPENSES']
    assert len(fin) == 1
    assert fin[0]['2023'] == 999999.0  # deterministic: dòng ĐẦU theo vendor row-order


# ---------------------------------------------------------------- R3 (verdict d33b184)

@pytest.mark.parametrize('schema', ['v328', 'v329'])
def test_r3_exact_key_golden_wide(fake_fundamental, schema):
    """F3: wide metadata phải đúng canonical id,item,level,order,unit — exact-key,
    cho CẢ fixture 3.2.8 và 3.2.9 (không chỉ assert matrix khác null)."""
    fake_fundamental.df_holder['df'] = _long_df(schema, YEARS)
    r = client.get('/api/v1/experiment/data/fun/equity/income_statement',
                   params={'symbol': 'VNM', 'limit': 3})
    assert r.status_code == 200
    rows = r.json()['data']
    keys = list(rows[0].keys())
    assert keys[:5] == ['id', 'item', 'level', 'order', 'unit'], f'keys={keys[:6]}'
    assert all(PERIOD_COL_RE.match(k) for k in keys[5:])


def test_r3_gross_profit_conflict_ambiguous(fake_fundamental):
    """F1: IS_GROSS_PROFIT là FE target ('LN gộp') — duplicate xung đột 100/999
    phải 500 ambiguous_metric, KHÔNG chọn 100 im lặng."""
    from routers.experiment_data_fun import _normalize_long_columns
    ndf = _normalize_long_columns(_long_df('v329', YEARS).copy())
    gp = ndf.iloc[[0]].copy()
    gp['id'] = 'IS_GROSS_PROFIT'
    gp['name'] = 'LN gộp'
    gp['value'] = 100.0
    gp2 = gp.copy()
    gp2['value'] = 999.0
    fake_fundamental.df_holder['df'] = pd.concat([ndf, gp, gp2], ignore_index=True)
    r = client.get('/api/v1/experiment/data/fun/equity/income_statement', params={'symbol': 'VNM'})
    assert r.status_code == 500
    assert 'ambiguous_metric' in r.json()['detail']
    assert 'IS_GROSS_PROFIT' in r.json()['detail']


def test_r3_gross_profit_identical_dup_deduped(fake_fundamental):
    from routers.experiment_data_fun import _normalize_long_columns
    ndf = _normalize_long_columns(_long_df('v329', YEARS).copy())
    gp = ndf.iloc[[0]].copy()
    gp['id'] = 'IS_GROSS_PROFIT'
    fake_fundamental.df_holder['df'] = pd.concat([ndf, gp, gp.copy()], ignore_index=True)
    r = client.get('/api/v1/experiment/data/fun/equity/income_statement', params={'symbol': 'VNM'})
    assert r.status_code == 200
    rows = r.json()['data']
    assert len([x for x in rows if x['id'] == 'IS_GROSS_PROFIT']) == 1


def test_r3_limit_annual_two_periods(fake_fundamental):
    """F2: statements limit=2 → đúng 2 kỳ mới nhất."""
    fake_fundamental.df_holder['df'] = _long_df('v329', YEARS)
    r = client.get('/api/v1/experiment/data/fun/equity/income_statement',
                   params={'symbol': 'VNM', 'limit': 2})
    rows = r.json()['data']
    pcols = [k for k in rows[0] if PERIOD_COL_RE.match(k)]
    assert sorted(pcols) == ['2024', '2025']


def test_r3_limit_quarterly_two_periods(fake_fundamental):
    fake_fundamental.df_holder['df'] = _long_df('v329', QUARTERS)
    r = client.get('/api/v1/experiment/data/fun/equity/balance_sheet',
                   params={'symbol': 'VNM', 'period_type': 2, 'limit': 2})
    rows = r.json()['data']
    pcols = [k for k in rows[0] if PERIOD_COL_RE.match(k)]
    assert sorted(pcols) == ['2025-Q3', '2026-Q1']


def test_r3_limit_ratio_two_periods(fake_fundamental):
    fake_fundamental.df_holder['df'] = _long_df('v329', QUARTERS + YEARS)
    r = client.get('/api/v1/experiment/data/fun/equity/ratio',
                   params={'symbol': 'VNM', 'period_type': 2, 'limit': 2})
    rows = r.json()['data']
    periods = {row['period'] for row in rows}
    assert sorted(periods) == ['2025-Q3', '2026-Q1']  # 2 kỳ mới nhất trong fixture hỗn hợp


# ------------------------------------------- R4 (SOL_R3_VERDICT_VN328 — F1)
# Replay verdict: period rác (None → 'None' sort sau '2025' / 'banana') chiếm
# suất limit TRƯỚC khi được kiểm → wide trả long rows. Fix: lọc hợp lệ (pattern
# + loại yêu cầu) TRƯỚC limit; hết hợp lệ → 500 no_valid_period fail-closed.

def _with_junk_rows(df, junk_periods):
    """Append row period rác (None/'banana') copy từ row đầu, value -1.0."""
    rows = []
    base = df.iloc[0].to_dict()
    for jp in junk_periods:
        r = dict(base)
        r['period'] = jp
        r['value'] = -1.0
        rows.append(r)
    return pd.concat([df, pd.DataFrame(rows)], ignore_index=True)


def test_r4_f1_none_period_cannot_displace_limit1_wide(fake_fundamental):
    """Replay ĐÚNG verdict: 2024/2025 + 1 row period=None, limit=1 (year) →
    wide contract giữ nguyên (id,item,level,order,unit + 2025), KHÔNG trả long."""
    df = _with_junk_rows(_long_df('v329', ['2024', '2025']), [None])
    fake_fundamental.df_holder['df'] = df
    r = client.get('/api/v1/experiment/data/fun/equity/income_statement',
                   params={'symbol': 'VNM', 'limit': 1})
    assert r.status_code == 200, r.text
    rows = r.json()['data']
    keys = list(rows[0].keys())
    assert 'period' not in keys and 'value' not in keys  # KHÔNG phải long rows
    assert keys[:5] == ['id', 'item', 'level', 'order', 'unit']
    pcols = [k for k in keys if PERIOD_COL_RE.match(k)]
    assert pcols == ['2025']  # None không chiếm suất


def test_r4_f1_none_period_not_consume_limit2(fake_fundamental):
    df = _with_junk_rows(_long_df('v329', ['2023', '2024', '2025']), [None])
    fake_fundamental.df_holder['df'] = df
    r = client.get('/api/v1/experiment/data/fun/equity/income_statement',
                   params={'symbol': 'VNM', 'limit': 2})
    assert r.status_code == 200
    pcols = [k for k in r.json()['data'][0] if PERIOD_COL_RE.match(k)]
    assert sorted(pcols) == ['2024', '2025']  # đủ 2 suất cho 2 năm hợp lệ


def test_r4_f1_nonperiod_string_quarterly(fake_fundamental):
    """'banana'/'None'-string ở request quarterly không chiếm suất limit."""
    df = _with_junk_rows(_long_df('v329', QUARTERS), ['banana', 'None'])
    fake_fundamental.df_holder['df'] = df
    r = client.get('/api/v1/experiment/data/fun/equity/income_statement',
                   params={'symbol': 'VNM', 'period_type': 2, 'limit': 2})
    assert r.status_code == 200
    pcols = [k for k in r.json()['data'][0] if PERIOD_COL_RE.match(k)]
    assert sorted(pcols) == ['2025-Q3', '2026-Q1']


def test_r4_f1_all_invalid_periods_fail_closed(fake_fundamental):
    """Toàn bộ period rác → 500 no_valid_period (fail-closed), KHÔNG bao giờ
    trả long rows từ default-wide path (đúng lỗi replay: 200 + keys long)."""
    df = _with_junk_rows(_long_df('v329', ['banana', 'xyz-9']), [None])
    fake_fundamental.df_holder['df'] = df
    r = client.get('/api/v1/experiment/data/fun/equity/income_statement',
                   params={'symbol': 'VNM'})
    assert r.status_code == 500
    assert 'no_valid_period' in r.json()['detail']


def test_r4_f1_cross_type_period_does_not_displace_year(fake_fundamental):
    """Kỳ HỢP LỆ nhưng SAI LOẠI (2026-Q1 trong request year, sort sau 2025)
    không chiếm suất limit của kỳ year."""
    fake_fundamental.df_holder['df'] = _long_df('v329', YEARS + QUARTERS)
    r = client.get('/api/v1/experiment/data/fun/equity/income_statement',
                   params={'symbol': 'VNM', 'period_type': 1, 'limit': 2})
    assert r.status_code == 200
    pcols = [k for k in r.json()['data'][0] if PERIOD_COL_RE.match(k)]
    assert sorted(pcols) == ['2024', '2025']  # không phải ['2025', '2026-Q1']


def test_r4_f1_long_path_junk_not_displace(fake_fundamental):
    """format=long: label rác không làm mất kỳ hợp lệ mới nhất."""
    df = _with_junk_rows(_long_df('v329', ['2024', '2025']), [None])
    fake_fundamental.df_holder['df'] = df
    r = client.get('/api/v1/experiment/data/fun/equity/income_statement',
                   params={'symbol': 'VNM', 'format': 'long', 'limit': 1})
    assert r.status_code == 200
    periods = {row['period'] for row in r.json()['data']}
    assert periods == {'2025'}
    assert 'None' not in periods and -1.0 not in [row['value'] for row in r.json()['data']]


def test_r4_f1_ratio_junk_not_displace(fake_fundamental):
    """Ratio path: period rác không chiếm suất kỳ hợp lệ."""
    df = _with_junk_rows(_long_df('v329', QUARTERS), [None])
    fake_fundamental.df_holder['df'] = df
    r = client.get('/api/v1/experiment/data/fun/equity/ratio',
                   params={'symbol': 'VNM', 'period_type': 2, 'limit': 1})
    assert r.status_code == 200
    periods = {row['period'] for row in r.json()['data']}
    assert periods == {'2026-Q1'}


# ------------------------------------------- R5 (SOL_R4_VERDICT_VN328 — F1)
# Replay: frame CÓ DỮ LIỆU nhưng THIẾU CỘT period/id từng thoát fail-closed
# (trả 200 raw long-like keys id,name,level,order,unit,value).

def _df_missing_column(column):
    base = {'id': 'IS_NET_REVENUE', 'name': 'Doanh thu', 'level': 1,
            'order': 1, 'unit': 'VNĐ', 'value': 100.0, 'period': '2025'}
    del base[column]
    return pd.DataFrame([base])


@pytest.mark.parametrize('missing', ['period', 'id'])
def test_r5_f1_missing_column_fail_closed(fake_fundamental, missing):
    """Frame có row nhưng thiếu cột period/id → 500 controlled marker —
    default-wide KHÔNG bao giờ trả name/value/period long keys."""
    fake_fundamental.df_holder['df'] = _df_missing_column(missing)
    r = client.get('/api/v1/experiment/data/fun/equity/income_statement',
                   params={'symbol': 'VNM', 'limit': 1})
    assert r.status_code == 500, r.text
    assert 'vendor_schema_missing_column' in r.json()['detail']
    assert missing in r.json()['detail']


def test_r5_f1_missing_column_balance_sheet_too(fake_fundamental):
    """Cùng lỗ hổng ở statement khác — fail-closed đồng nhất."""
    fake_fundamental.df_holder['df'] = _df_missing_column('period')
    r = client.get('/api/v1/experiment/data/fun/equity/balance_sheet',
                   params={'symbol': 'VNM'})
    assert r.status_code == 500
    assert 'vendor_schema_missing_column' in r.json()['detail']


def test_r5_f1_empty_vendor_frame_still_passthrough(fake_fundamental):
    """Vendor 0 row (genuine no-data) giữ pass-through 200 [] như cũ —
    phân biệt với frame có dữ liệu thiếu schema."""
    fake_fundamental.df_holder['df'] = pd.DataFrame()
    r = client.get('/api/v1/experiment/data/fun/equity/income_statement',
                   params={'symbol': 'VNM'})
    assert r.status_code == 200
    assert r.json()['data'] == []
