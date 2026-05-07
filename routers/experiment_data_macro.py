from fastapi import APIRouter, HTTPException, Query
import pandas as pd
from vnstock_data import Macro

router = APIRouter(prefix="/api/v1/experiment/data/macro", tags=["Experiment Data Macro"])

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
# Economy
# --------------------------------------------------------------------------------
@router.get("/economy/gdp")
def economy_gdp(start: str = None, end: str = None, period: str = "quarter", length: int = None):
    try: return {"data": _clean_dataframe(Macro().economy().gdp(start=start, end=end, period=period, length=length))}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/economy/cpi")
def economy_cpi(start: str = None, end: str = None, period: str = "month", length: int = None):
    try: return {"data": _clean_dataframe(Macro().economy().cpi(start=start, end=end, period=period, length=length))}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/economy/industry_prod")
def economy_industry_prod(start: str = None, end: str = None, period: str = "month", length: int = None):
    try: return {"data": _clean_dataframe(Macro().economy().industry_prod(start=start, end=end, period=period, length=length))}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/economy/import_export")
def economy_import_export(start: str = None, end: str = None, period: str = "month", length: int = None):
    try: return {"data": _clean_dataframe(Macro().economy().import_export(start=start, end=end, period=period, length=length))}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/economy/retail")
def economy_retail(start: str = None, end: str = None, period: str = "month", length: int = None):
    try: return {"data": _clean_dataframe(Macro().economy().retail(start=start, end=end, period=period, length=length))}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/economy/fdi")
def economy_fdi(start: str = None, end: str = None, period: str = "month", length: int = None):
    try: return {"data": _clean_dataframe(Macro().economy().fdi(start=start, end=end, period=period, length=length))}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/economy/money_supply")
def economy_money_supply(start: str = None, end: str = None, period: str = "month", length: int = None):
    try: return {"data": _clean_dataframe(Macro().economy().money_supply(start=start, end=end, period=period, length=length))}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/economy/population_labor")
def economy_population_labor(start: str = None, end: str = None, period: str = "year", length: int = None):
    try: return {"data": _clean_dataframe(Macro().economy().population_labor(start=start, end=end, period=period, length=length))}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))


# --------------------------------------------------------------------------------
# Currency
# --------------------------------------------------------------------------------
@router.get("/currency/exchange_rate")
def currency_exchange_rate(start: str = None, end: str = None, period: str = "day", length: int = None):
    try: return {"data": _clean_dataframe(Macro().currency().exchange_rate(start=start, end=end, period=period, length=length))}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/currency/interest_rate")
def currency_interest_rate(start: str = None, end: str = None, period: str = "day", format: str = "pivot", length: int = None):
    try: return {"data": _clean_dataframe(Macro().currency().interest_rate(start=start, end=end, period=period, format=format, length=length))}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))


# --------------------------------------------------------------------------------
# Commodity
# --------------------------------------------------------------------------------
@router.get("/commodity/gold")
def commodity_gold(market: str = "VN", start: str = None, end: str = None, length: int = None):
    try: return {"data": _clean_dataframe(Macro().commodity().gold(market=market, start=start, end=end, length=length))}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/commodity/gas")
def commodity_gas(market: str = "VN", start: str = None, end: str = None, length: int = None):
    try: return {"data": _clean_dataframe(Macro().commodity().gas(market=market, start=start, end=end, length=length))}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/commodity/oil_crude")
def commodity_oil_crude(start: str = None, end: str = None, length: int = None):
    try: return {"data": _clean_dataframe(Macro().commodity().oil_crude(start=start, end=end, length=length))}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/commodity/coke")
def commodity_coke(start: str = None, end: str = None, length: int = None):
    try: return {"data": _clean_dataframe(Macro().commodity().coke(start=start, end=end, length=length))}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/commodity/steel")
def commodity_steel(market: str = "VN", start: str = None, end: str = None, length: int = None):
    try: return {"data": _clean_dataframe(Macro().commodity().steel(market=market, start=start, end=end, length=length))}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/commodity/iron_ore")
def commodity_iron_ore(start: str = None, end: str = None, length: int = None):
    try: return {"data": _clean_dataframe(Macro().commodity().iron_ore(start=start, end=end, length=length))}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/commodity/fertilizer_ure")
def commodity_fertilizer_ure(start: str = None, end: str = None, length: int = None):
    try: return {"data": _clean_dataframe(Macro().commodity().fertilizer_ure(start=start, end=end, length=length))}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/commodity/soybean")
def commodity_soybean(start: str = None, end: str = None, length: int = None):
    try: return {"data": _clean_dataframe(Macro().commodity().soybean(start=start, end=end, length=length))}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/commodity/corn")
def commodity_corn(start: str = None, end: str = None, length: int = None):
    try: return {"data": _clean_dataframe(Macro().commodity().corn(start=start, end=end, length=length))}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/commodity/sugar")
def commodity_sugar(start: str = None, end: str = None, length: int = None):
    try: return {"data": _clean_dataframe(Macro().commodity().sugar(start=start, end=end, length=length))}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/commodity/pork")
def commodity_pork(market: str = "VN", start: str = None, end: str = None, length: int = None):
    try: return {"data": _clean_dataframe(Macro().commodity().pork(market=market, start=start, end=end, length=length))}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))
