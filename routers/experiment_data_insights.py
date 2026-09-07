from fastapi import APIRouter, HTTPException, Query, Body
from routers._serde import _clean_dataframe
from vnstock_data import Insights
from typing import Optional, Dict, Any

router = APIRouter(prefix="/api/v1/experiment/data/insights", tags=["Experiment Data Insights"])

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
