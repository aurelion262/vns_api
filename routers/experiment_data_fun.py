from fastapi import APIRouter, HTTPException, Query
import pandas as pd
from vnstock_data import Fundamental

router = APIRouter(prefix="/api/v1/experiment/data/fun", tags=["Experiment Data Fundamental"])

def _clean_dataframe(df):
    if df is None:
        return []
    if isinstance(df, pd.DataFrame):
        if df.empty:
            return []
        # Flatten MultiIndex columns if any
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = ['_'.join(map(str, col)).strip() for col in df.columns.values]
        df_clean = df.astype(object).where(pd.notnull(df), None)
        return df_clean.to_dict(orient="records")
    elif isinstance(df, dict):
        return [df]
    elif isinstance(df, list):
        return df
    return []

# --------------------------------------------------------------------------------
# Equity Fundamental
# --------------------------------------------------------------------------------

@router.get("/equity/income_statement")
def equity_income_statement(
    symbol: str = Query(...), 
    limit: int = Query(4), 
    period_type: int = Query(1, description="1=Năm, 2=Quý"), 
    lang: str = Query("vi")
):
    try: return {"data": _clean_dataframe(Fundamental().equity(symbol.upper()).income_statement(limit=limit, period_type=period_type, lang=lang))}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/equity/balance_sheet")
def equity_balance_sheet(
    symbol: str = Query(...), 
    limit: int = Query(4), 
    period_type: int = Query(1), 
    lang: str = Query("vi")
):
    try: return {"data": _clean_dataframe(Fundamental().equity(symbol.upper()).balance_sheet(limit=limit, period_type=period_type, lang=lang))}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/equity/cash_flow")
def equity_cash_flow(
    symbol: str = Query(...), 
    limit: int = Query(4), 
    period_type: int = Query(1), 
    lang: str = Query("vi")
):
    try: return {"data": _clean_dataframe(Fundamental().equity(symbol.upper()).cash_flow(limit=limit, period_type=period_type, lang=lang))}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/equity/ratio")
def equity_ratio(
    symbol: str = Query(...), 
    limit: int = Query(4), 
    period_type: int = Query(1), 
    lang: str = Query("vi")
):
    try: return {"data": _clean_dataframe(Fundamental().equity(symbol.upper()).ratio(limit=limit, period_type=period_type, lang=lang))}
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
