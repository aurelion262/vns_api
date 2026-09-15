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


# Bộ id FE thực sự đọc (vasAdapter.ts mapping — verdict P2-2: conflict-check
# CHỈ target; live 3.2.9 chứng minh duplicate conflicting ở non-target id là
# bình thường — vd sub-item "Trong đó:" gộp id cha với giá trị khác).
_FE_TARGET_IDS = frozenset({
    'IS_NET_REVENUE', 'IS_REVENUE',
    'IS_INTEREST_INCOME_AND_SIMILAR_INCOME',
    'IS_TOTAL_NET_REVENUE_FROM_INSURANCE_BUSINESS',
    'IS_OPERATING_PROFIT',
    'IS_OPERATING_PROFIT_BEFORE_PROVISION_FOR_CREDIT_LOSSES',
    'IS_NET_PROFIT_AFTER_TAX',
    'IS_PROFIT_AFTER_TAX_FOR_SHAREHOLDERS_OF_PARENT_COMPANY',
    'IS_BASIC_EARNINGS_PER_SHARE',
})


def _long_to_stable_wide(df):
    """Vendor long (3.2.8 hoặc 3.2.9) → wide STABLE cho FE: dòng = chỉ tiêu,
    cột = kỳ ('2018', '2018-Q1'...).
    - TARGET id (FE đọc): duplicate identical → dedupe; giá trị xung đột →
      ValueError ambiguous_metric (KHÔNG chọn first).
    - Non-target: duplicate conflicting là bình thường trong live data →
      drop_duplicates giữ dòng đầu (đ / row-order vendor, deterministic)."""
    import pandas as pd
    df = _normalize_long_columns(df)
    if df is None or df.empty or 'period' not in df.columns or 'id' not in df.columns:
        return df
    df = df.copy()
    df['period'] = df['period'].astype(str)
    periods = sorted(p for p in df['period'].unique() if _PERIOD_RE.match(p))
    if not periods:
        return df
    sub = df[df['period'].isin(periods)]

    tgt_dup = sub[sub['id'].isin(_FE_TARGET_IDS)].duplicated(['id', 'period'], keep=False)
    if tgt_dup.any():
        target_rows = sub[sub['id'].isin(_FE_TARGET_IDS)]
        nunique = target_rows[target_rows.duplicated(['id', 'period'], keep=False)]             .groupby(['id', 'period'])['value'].nunique(dropna=False)
        if (nunique > 1).any():
            keys = '; '.join(f'{k[0]}@{k[1]}' for k in nunique[nunique > 1].index[:5])
            raise ValueError(f'ambiguous_metric: giá trị xung đột (id, period): {keys}')
    sub = sub.drop_duplicates(['id', 'period'], keep='first')
    meta_cols = [c for c in ('id', 'name', 'level', 'order', 'unit') if c in sub.columns]
    meta = sub.groupby('id', as_index=False)[[c for c in meta_cols if c != 'id']].first()
    piv = sub.pivot(index='id', columns='period', values='value').reset_index()
    piv = piv[['id'] + periods]
    out = meta.merge(piv, on='id', how='right')
    ordered = meta_cols + periods
    return out[[c for c in ordered if c in out.columns]].reset_index(drop=True)


def _statement_response(method: str, symbol: str, limit: int, period_type: int, lang: str, fmt: str):
    """Finance adapter: taxonomy VAS áp mọi bản (IS_*/RT_* — verify live 15/9:
    Fundamental không-format trả raw isa1* nên KHÔNG dùng cho statement/ratio).
    limit giữ cho tương thích query công khai; Finance tự giới hạn lịch sử mặc định."""
    period = 'year' if int(period_type) == 1 else 'quarter'
    fin = Finance(symbol=symbol.upper(), source='VCI', period=period)
    df = getattr(fin, method)(lang=lang)  # vendor long mọi bản
    if fmt == 'long':
        return {"data": _clean_dataframe(_normalize_long_columns(df))}
    return {"data": _clean_dataframe(_long_to_stable_wide(df))}


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
        return {"data": _clean_dataframe(_normalize_long_columns(fin.ratio(lang=lang)))}
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
