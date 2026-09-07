from fastapi import APIRouter, HTTPException, Query
import pandas as pd
from routers._serde import _clean_dataframe
from vnstock_data import Analytics

router = APIRouter(prefix="/api/v1/experiment/data/analytics", tags=["Experiment Data Analytics"])

# --------------------------------------------------------------------------------
# Valuation
# --------------------------------------------------------------------------------
@router.get("/valuation/pe")
def valuation_pe(index: str = Query("VNINDEX"), duration: str = Query("5Y")):
    try: return {"data": _clean_dataframe(Analytics().valuation(index).pe(duration=duration))}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/valuation/pb")
def valuation_pb(index: str = Query("VNINDEX"), duration: str = Query("5Y")):
    try: return {"data": _clean_dataframe(Analytics().valuation(index).pb(duration=duration))}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/valuation/evaluation")
def valuation_evaluation(index: str = Query("VNINDEX"), duration: str = Query("5Y")):
    try: return {"data": _clean_dataframe(Analytics().valuation(index).evaluation(duration=duration))}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))
