from fastapi import APIRouter, HTTPException, Query, Body
import pandas as pd
from vnstock_data import Insights
from typing import Optional, Dict, Any

router = APIRouter(prefix="/api/v1/experiment/data/insights", tags=["Experiment Data Insights"])

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
    return []

# --------------------------------------------------------------------------------
# Ranking
# --------------------------------------------------------------------------------
@router.get("/ranking/gainer")
def ranking_gainer(index: str = None, limit: int = 10):
    try: return {"data": _clean_dataframe(Insights().ranking().gainer(index=index, limit=limit))}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/ranking/loser")
def ranking_loser(index: str = None, limit: int = 10):
    try: return {"data": _clean_dataframe(Insights().ranking().loser(index=index, limit=limit))}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/ranking/value")
def ranking_value(index: str = None, limit: int = 10):
    try: return {"data": _clean_dataframe(Insights().ranking().value(index=index, limit=limit))}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/ranking/volume")
def ranking_volume(index: str = None, limit: int = 10):
    try: return {"data": _clean_dataframe(Insights().ranking().volume(index=index, limit=limit))}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/ranking/foreign_buy")
def ranking_foreign_buy(date: str = None, limit: int = 10):
    try: return {"data": _clean_dataframe(Insights().ranking().foreign_buy(date=date, limit=limit))}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/ranking/foreign_sell")
def ranking_foreign_sell(date: str = None, limit: int = 10):
    try: return {"data": _clean_dataframe(Insights().ranking().foreign_sell(date=date, limit=limit))}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/ranking/deal")
def ranking_deal(index: str = None, limit: int = 10):
    try: return {"data": _clean_dataframe(Insights().ranking().deal(index=index, limit=limit))}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

# --------------------------------------------------------------------------------
# Screener
# --------------------------------------------------------------------------------
@router.get("/screener/criteria")
def screener_criteria(lang: str = "vi"):
    try: return {"data": _clean_dataframe(Insights().screener().criteria(lang=lang))}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.post("/screener/filter")
def screener_filter(
    payload: Optional[Dict[str, Any]] = Body(None),
    limit: int = Query(2000)
):
    try: return {"data": _clean_dataframe(Insights().screener().filter(params=payload, limit=limit))}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))
