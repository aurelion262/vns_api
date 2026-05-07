from fastapi import APIRouter, HTTPException, Query
import pandas as pd
from vnstock_data import Reference
from vnstock_data.explorer.kbs.company import Company as KBSCompany
from vnstock_data.explorer.vci.company import Company as VCICompany
from vnstock_data.explorer.kbs.listing import Listing as KBSListing
router = APIRouter(prefix="/api/v1/experiment/data/reference", tags=["Experiment Data Reference"])

def _clean_dataframe(df):
    if df is None:
        return []
    if isinstance(df, pd.DataFrame):
        if df.empty:
            return []
        df_clean = df.where(pd.notnull(df), None)
        return df_clean.to_dict(orient="records")
    elif isinstance(df, dict):
        return [df]
    elif isinstance(df, list):
        return df
    return []

def get_ref():
    return Reference()

# 1. Company
@router.get("/company/info")
def company_info(symbol: str = Query(..., description="Mã chứng khoán, VD: TCB")):
    try: return {"data": _clean_dataframe(KBSCompany(symbol.upper()).overview())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/company/shareholders")
def company_shareholders(symbol: str = Query(..., description="Mã chứng khoán")):
    try: return {"data": _clean_dataframe(KBSCompany(symbol.upper()).shareholders())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/company/officers")
def company_officers(symbol: str = Query(..., description="Mã chứng khoán")):
    try: return {"data": _clean_dataframe(KBSCompany(symbol.upper()).officers())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/company/subsidiaries")
def company_subsidiaries(symbol: str = Query(..., description="Mã chứng khoán")):
    try: return {"data": _clean_dataframe(KBSCompany(symbol.upper()).subsidiaries())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/company/news")
def company_news(symbol: str = Query(..., description="Mã chứng khoán")):
    try: return {"data": _clean_dataframe(VCICompany(symbol.upper()).news())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/company/events")
def company_events(symbol: str = Query(..., description="Mã chứng khoán")):
    try: 
        import requests
        url = f"https://api.simplize.vn/api/company/events/list?ticker={symbol.upper()}&page=0&size=50"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            res_data = r.json()
            if "data" in res_data and res_data["data"]:
                import pandas as pd
                return {"data": _clean_dataframe(pd.DataFrame(res_data["data"]))}
        return {"data": []}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/company/margin_ratio")
def company_margin_ratio(symbol: str = Query(..., description="Mã chứng khoán")):
    try:
        return {"data": _clean_dataframe(KBSCompany(symbol.upper()).margin_ratio())}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Không có data từ nguồn dữ liệu gốc (KBS đang lỗi 404)")

# 2. Equity
@router.get("/equity/list")
def equity_list():
    try: return {"data": _clean_dataframe(KBSListing().all_symbols())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/equity/list_by_group")
def equity_list_by_group(group: str = Query(..., description="Nhóm, VD: VN30")):
    try: return {"data": _clean_dataframe(KBSListing().symbols_by_group(group.upper()))}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/equity/list_by_exchange")
def equity_list_by_exchange():
    try: return {"data": _clean_dataframe(KBSListing().symbols_by_exchange())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/equity/list_by_industry")
def equity_list_by_industry():
    try: return {"data": _clean_dataframe(KBSListing().symbols_by_industries())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

# 3. Index
@router.get("/index/list")
def index_list():
    try: return {"data": _clean_dataframe(get_ref().index.list())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/index/groups")
def index_groups():
    try: return {"data": _clean_dataframe(get_ref().index.groups())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/index/members")
def index_members(group: str = Query(..., description="Nhóm, VD: VN30")):
    try: return {"data": _clean_dataframe(get_ref().index.members(group.upper()))}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/index/list_by_group")
def index_list_by_group(group: str = Query(..., description="Nhóm, VD: HOSE")):
    try: return {"data": _clean_dataframe(get_ref().index.list_by_group(group.upper()))}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

# 4. Industry
@router.get("/industry/list")
def industry_list():
    try: return {"data": _clean_dataframe(get_ref().industry.list())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/industry/sectors")
def industry_sectors():
    try: return {"data": _clean_dataframe(get_ref().industry.sectors())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

# 5. Fund
@router.get("/fund/list")
def fund_list():
    try: return {"data": _clean_dataframe(get_ref().fund.list())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

# 6. ETF
@router.get("/etf/list")
def etf_list():
    try: return {"data": _clean_dataframe(get_ref().etf.list())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

# 7. Bond
@router.get("/bond/list")
def bond_list(bond_type: str = Query("all", description="all, corporate, government")):
    try: return {"data": _clean_dataframe(get_ref().bond.list(bond_type=bond_type))}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

# 8. Events
@router.get("/events/calendar")
def events_calendar(
    start: str = Query(..., description="Start Date YYYY-MM-DD"),
    end: str = Query(..., description="End Date YYYY-MM-DD"),
    event_type: str = Query(None, description="dividend, insider, agm, others")
):
    try:
        kwargs = {"start": start, "end": end}
        if event_type: kwargs["event_type"] = event_type
        return {"data": _clean_dataframe(get_ref().events.calendar(**kwargs))}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/events/market")
def events_market():
    try: return {"data": _clean_dataframe(get_ref().events.market())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

# 9. Search
@router.get("/search/symbol")
def search_symbol(
    query: str = Query(..., description="Search term, e.g., VNM"),
    locale: str = Query("vi-vn", description="Locale"),
    limit: int = Query(10, description="Limit")
):
    try: return {"data": _clean_dataframe(get_ref().search.symbol(query=query, locale=locale, limit=limit))}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

# 10. Futures
@router.get("/futures/list")
def futures_list():
    try: return {"data": _clean_dataframe(get_ref().futures().list())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/futures/info")
def futures_info(symbol: str = Query(..., description="Symbol")):
    try: return {"data": _clean_dataframe(get_ref().futures(symbol.upper()).info())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

# 11. Warrant
@router.get("/warrant/list")
def warrant_list():
    try: return {"data": _clean_dataframe(get_ref().warrant().list())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/warrant/info")
def warrant_info(symbol: str = Query(..., description="Symbol")):
    try: return {"data": _clean_dataframe(get_ref().warrant(symbol.upper()).info())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))
