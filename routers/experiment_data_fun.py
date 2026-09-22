from fastapi import APIRouter, HTTPException, Query
from routers._serde import _clean_dataframe
# Guard canonical (P1-2 verdict Codex 2191d4c): main.py + routers/__init__.py áp
# trước import này; giữ import ở đây để file tự đứng được khi import trực tiếp.
from guard_vnstock import apply_vnstock_agent_guard

apply_vnstock_agent_guard()

from vnstock_data import Fundamental  # note/financial_health (Fundamental-only)
from vnstock_data.api.financial import Finance  # statements + ratio: taxonomy VAS (IS_*/RT_*) luôn áp

router = APIRouter(prefix="/api/v1/experiment/data/fun", tags=["Experiment Data Fundamental"])

# --------------------------------------------------------------------------------
# Equity Fundamental — vnstock_data 3.2.8/3.2.9 (VAS unified ids IS_*/BS_*/CF_*).
# CONTRACT ỔN ĐỊNH (P1-1 verdict Codex 2191d4c — FE st0nks_web vasAdapter.ts):
#   - 3 statement endpoint: default `wide` với schema STABLE của Stoxlab — mỗi dòng
#     1 chỉ tiêu {id, name, level?, order?, unit?, '2018' | '2018-Q1', ...} — vns_api
#     TỰ PIVOT từ vendor long (3.2.9 wide regression trả raw VCI fields, không dùng).
#     `format=long` chỉ opt-in tường minh (keys cũng chuẩn hóa về id/name).
#   - ratio: luôn long STABLE keys {period, id, name, order, level, unit, value}
#     (FE đọc r.id — 3.2.9 đổi item_id/item phải normalize lại).
# Vendor luôn được gọi KHÔNG format (default long ở cả 3.2.8/3.2.9) → một đường
# code duy nhất, output giống hệt trên hai bản (contract test chứng minh).
# --------------------------------------------------------------------------------

def _format_param():
    return Query("wide", description="wide (mặc định — schema ổn định Stoxlab, tự pivot từ vendor long) | long (opt-in)")


def _normalize_long_columns(df):
    """Đưa long của 3.2.9 (item_id/item/display_order) về keys ổn định 3.2.8 (id/name/order)."""
    if df is None or getattr(df, 'empty', True):
        return df
    ren = {}
    if 'item_id' in df.columns:
        ren['item_id'] = 'id'
    if 'item' in df.columns:
        ren['item'] = 'name'
    if 'display_order' in df.columns:
        ren['display_order'] = 'order'
    return df.rename(columns=ren) if ren else df


_PERIOD_RE_STR = r'^20\d{2}(-Q[1-4])?$'

import re as _re
_PERIOD_RE = _re.compile(_PERIOD_RE_STR)

# F1 (SOL_R3_VERDICT_VN328): pattern period theo LOẠI yêu cầu (year|quarter)
_PERIOD_KIND_RE = {
    'year': _re.compile(r'^20\d{2}$'),
    'quarter': _re.compile(r'^20\d{2}-Q[1-4]$'),
}


def _period_kind(period_type) -> str:
    return 'year' if int(period_type) == 1 else 'quarter'


def _filter_valid_periods(df, kind=None):
    """F1 (SOL_R3_VERDICT_VN328): loại row có period KHÔNG hợp lệ (None/
    'banana'/'None'-string/sai loại year|quarter so với yêu cầu) TRƯỚC khi
    đếm limit — period rác KHÔNG được phép chiếm suất limit. Trả df chỉ còn
    period hợp lệ (df nguyên vẹn nếu không phải long có cột period)."""
    if df is None or getattr(df, 'empty', True) or 'period' not in df.columns:
        return df
    pat = _PERIOD_KIND_RE.get(kind) if kind else _PERIOD_RE
    df = df.copy()
    df['period'] = df['period'].astype(str)
    return df[df['period'].map(lambda p: bool(pat.match(p)))]


# Target conflict set KHÓA theo đúng danh sách metric FE canonical
# (st0nks_web/src/lib/vasAdapter.ts INCOME_METRIC_IDS — R3 F1 verdict d33b184:
# thiếu IS_GROSS_PROFIT từng khiến duplicate xung đột 100/999 bị chọn 100 im lặng)
# + IS_BASIC_EARNINGS_PER_SHARE (consumer stoxlab quarterly đọc EPS).
# Non-target duplicate conflicting là bình thường trong live data — vd sub-item
# "Trong đó:" gộp id cha với giá trị khác.
_FE_TARGET_IDS = frozenset({
    # 'Doanh thu'
    'IS_NET_REVENUE', 'IS_REVENUE',
    'IS_INTEREST_INCOME_AND_SIMILAR_INCOME',
    'IS_TOTAL_NET_REVENUE_FROM_INSURANCE_BUSINESS',
    # 'LN gộp'
    'IS_GROSS_PROFIT',
    # 'LN từ HĐKD'
    'IS_OPERATING_PROFIT',
    'IS_OPERATING_PROFIT_BEFORE_PROVISION_FOR_CREDIT_LOSSES',
    # 'LNST'
    'IS_NET_PROFIT_AFTER_TAX',
    'IS_PROFIT_AFTER_TAX_FOR_SHAREHOLDERS_OF_PARENT_COMPANY',
    # stoxlab quarterly consumer
    'IS_BASIC_EARNINGS_PER_SHARE',
})


def _long_to_stable_wide(df, kind=None, limit=None):
    """Vendor long (3.2.8 hoặc 3.2.9) → wide STABLE cho FE: dòng = chỉ tiêu,
    cột = kỳ ('2018', '2018-Q1'...).
    - TARGET id (FE đọc): duplicate identical → dedupe; giá trị xung đột →
      ValueError ambiguous_metric (KHÔNG chọn first).
    - Non-target: duplicate conflicting là bình thường trong live data →
      drop_duplicates giữ dòng đầu (đ / row-order vendor, deterministic).
    - F1 (SOL_R3_VERDICT_VN328): lọc period hợp lệ (pattern + LOẠI yêu cầu)
      TRƯỚC khi lấy N kỳ limit — period rác không chiếm suất. Có row mà hết
      hợp lệ → ValueError no_valid_period (fail-closed): default-wide
      KHÔNG BAO GIỜ trả long rows. Vendor 0 row → pass-through như cũ."""
    import pandas as pd
    df = _normalize_long_columns(df)
    if df is None or 'period' not in df.columns or 'id' not in df.columns:
        return df
    if df.empty:
        return df  # vendor trả 0 row — không phải lỗi period
    sub = _filter_valid_periods(df, kind)
    if sub is None or sub.empty:
        raise ValueError(
            'no_valid_period: vendor period toàn rác/sai loại '
            f'(kind={kind or "any"}) — từ chối trả wide (fail-closed)')
    if limit is not None:
        try:
            n = max(1, int(limit))
        except (TypeError, ValueError):
            n = None
        if n is not None:
            keep = sorted(sub['period'].unique())[-n:]
            sub = sub[sub['period'].isin(keep)]
    periods = sorted(sub['period'].unique())

    tgt_dup = sub[sub['id'].isin(_FE_TARGET_IDS)].duplicated(['id', 'period'], keep=False)
    if tgt_dup.any():
        target_rows = sub[sub['id'].isin(_FE_TARGET_IDS)]
        nunique = target_rows[target_rows.duplicated(['id', 'period'], keep=False)]             .groupby(['id', 'period'])['value'].nunique(dropna=False)
        if (nunique > 1).any():
            keys = '; '.join(f'{k[0]}@{k[1]}' for k in nunique[nunique > 1].index[:5])
            raise ValueError(f'ambiguous_metric: giá trị xung đột (id, period): {keys}')
    sub = sub.drop_duplicates(['id', 'period'], keep='first')
    # F3 (verdict d33b184): golden wide metadata = id,ITEM,level,order,unit
    # (long/ratio giữ contract id/name). Dùng set_index/join — không merge-on-column.
    meta_cols = [c for c in ('id', 'name', 'level', 'order', 'unit') if c in sub.columns]
    meta = sub.drop_duplicates('id', keep='first')[meta_cols]         .rename(columns={'name': 'item'}).set_index('id')
    piv = sub.pivot(index='id', columns='period', values='value')
    out = meta.join(piv, how='right').reset_index()
    ordered = ['id'] + [('item' if m == 'name' else m) for m in meta_cols if m != 'id'] + periods
    return out.reindex(columns=[c for c in ordered if c in out.columns])


def _limit_periods(df, limit, kind=None):
    """F2 (verdict d33b184): áp limit — chỉ giữ N KỲ MỚI NHẤT (long đã
    normalize, cột period dạng str). Trả df lọc; không đổi nếu thiếu cột/
    limit không hợp lệ.
    F1 (SOL_R3_VERDICT_VN328): lọc period hợp lệ (pattern + loại yêu cầu)
    TRƯỚC khi lấy N kỳ mới nhất — period rác không chiếm suất."""
    try:
        n = max(1, int(limit))
    except (TypeError, ValueError):
        return df
    df = _filter_valid_periods(df, kind)
    if df is None or getattr(df, 'empty', True) or 'period' not in df.columns:
        return df
    keep = sorted(df['period'].unique())[-n:]
    return df[df['period'].isin(keep)]


def _statement_response(method: str, symbol: str, limit: int, period_type: int, lang: str, fmt: str):
    """Finance adapter: taxonomy VAS áp mọi bản (IS_*/RT_* — verify live 15/9:
    Fundamental không-format trả raw isa1* nên KHÔNG dùng cho statement/ratio).
    limit (F2): N kỳ mới nhất — áp SAU normalize cho cả wide và long.
    F1 (SOL_R3): lọc period theo LOẠI yêu cầu (year|quarter) trước limit."""
    period = 'year' if int(period_type) == 1 else 'quarter'
    kind = _period_kind(period_type)
    fin = Finance(symbol=symbol.upper(), source='VCI', period=period)
    df = _normalize_long_columns(getattr(fin, method)(lang=lang))  # vendor long mọi bản
    if fmt == 'long':
        return {"data": _clean_dataframe(_limit_periods(df, limit, kind))}
    return {"data": _clean_dataframe(_long_to_stable_wide(df, kind, limit=limit))}


@router.get("/equity/income_statement")
def equity_income_statement(
    symbol: str = Query(...),
    limit: int = Query(4),
    period_type: int = Query(1, description="1=Năm, 2=Quý"),
    lang: str = Query("vi"),
    format: str = _format_param(),
):
    try: return _statement_response("income_statement", symbol, limit, period_type, lang, format)
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/equity/balance_sheet")
def equity_balance_sheet(
    symbol: str = Query(...),
    limit: int = Query(4),
    period_type: int = Query(1),
    lang: str = Query("vi"),
    format: str = _format_param(),
):
    try: return _statement_response("balance_sheet", symbol, limit, period_type, lang, format)
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/equity/cash_flow")
def equity_cash_flow(
    symbol: str = Query(...),
    limit: int = Query(4),
    period_type: int = Query(1),
    lang: str = Query("vi"),
    format: str = _format_param(),
):
    try: return _statement_response("cash_flow", symbol, limit, period_type, lang, format)
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/equity/ratio")
def equity_ratio(
    symbol: str = Query(...), 
    limit: int = Query(4), 
    period_type: int = Query(1), 
    lang: str = Query("vi")
):
    try:
        period = 'year' if int(period_type) == 1 else 'quarter'
        fin = Finance(symbol=symbol.upper(), source='VCI', period=period)
        df = _normalize_long_columns(fin.ratio(lang=lang))
        # F1 (SOL_R3): ratio cũng lọc period hợp lệ theo loại trước limit
        return {"data": _clean_dataframe(
            _limit_periods(df, limit, _period_kind(period_type)))}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/equity/note")
def equity_note(symbol: str = Query(...)):
    try: return {"data": _clean_dataframe(Fundamental().equity(symbol.upper()).note())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/equity/financial_health")
def equity_financial_health(
    symbol: str = Query(...), 
    scorecard: str = Query("auto", description="auto, banking, securities, insurance, generic"), 
    lang: str = Query("vi"), 
    limit: int = Query(4),
    reports: str = Query(None, description="Comma separated list of reports (income_statement, balance_sheet, cash_flow, ratio). Defaults to all if empty.")
):
    try:
        kwargs = {
            "scorecard": scorecard,
            "lang": lang,
            "limit": limit
        }
        if reports:
            kwargs["reports"] = [r.strip() for r in reports.split(",") if r.strip()]
            
        return {"data": _clean_dataframe(Fundamental().equity(symbol.upper()).financial_health(**kwargs))}
    except Exception as e: 
        raise HTTPException(status_code=500, detail=str(e))
