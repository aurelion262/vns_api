from fastapi import APIRouter, HTTPException, Query
import pandas as pd
from vnstock.ui import Retail

router = APIRouter(prefix="/api/v1/experiment/data/retail", tags=["Experiment Data Retail"])

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
# Retail (Gold & Exchange Rate)
# Note: vnstock_data v4 exposes these through Macro under the hood for sponsors,
# but we wrap them in the Retail domain as defined in Unified UI v4 docs.
# --------------------------------------------------------------------------------

@router.get("/gold")
def retail_gold(source: str = Query("sjc", description="sjc or btmc"), date: str = Query(None, description="YYYY-MM-DD")):
    try: 
        # In Retail domain, gold uses source="sjc" or "btmc" and date
        kwargs = {}
        if date:
            kwargs["date"] = date
        if source:
            kwargs["source"] = source
        return {"data": _clean_dataframe(Retail().gold(**kwargs))}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/exchange_rate")
def retail_exchange_rate(date: str = Query(None, description="YYYY-MM-DD")):
    try: 
        kwargs = {}
        if date:
            kwargs["date"] = date
        return {"data": _clean_dataframe(Retail().exchange_rate(**kwargs))}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))
