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
# vnstock_data 3.2.8: UI-chain Macro().economy().<method>() chỉ trả dữ liệu đúng khi
# gọi KHÔNG tham số. Truyền `period` (bất kỳ giá trị) → vendor upstream 404; truyền
# `length` → DataFrame rỗng. Default nội bộ của vendor từng metric đã khớp kỳ vọng
# (gdp=quarter, cpi/industry_prod/...=month, population_labor=year). Query params
# client gửi thêm (period/length/start/end) bị FastAPI bỏ qua.
# Debt VNSTOCK-328-FOLLOWUP: khôi phục period/length khi vendor sửa ở bản kế tiếp.
def _economy(method: str):
    fn = getattr(Macro().economy(), method)
    return {"data": _clean_dataframe(fn())}

@router.get("/economy/gdp")
def economy_gdp():
    try: return _economy("gdp")
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/economy/cpi")
def economy_cpi():
    try: return _economy("cpi")
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/economy/industry_prod")
def economy_industry_prod():
    try: return _economy("industry_prod")
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/economy/import_export")
def economy_import_export():
    try: return _economy("import_export")
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/economy/retail")
def economy_retail():
    try: return _economy("retail")
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/economy/fdi")
def economy_fdi():
    try: return _economy("fdi")
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/economy/money_supply")
def economy_money_supply():
    try: return _economy("money_supply")
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/economy/population_labor")
def economy_population_labor():
    try: return _economy("population_labor")
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
