from fastapi import APIRouter, HTTPException, Query
import pandas as pd
from vnstock_data import Reference, Market, Fundamental
from vnstock_ta import Indicator
from vnstock_news import Crawler

router = APIRouter(prefix="/api/v1/experiment", tags=["Experiment"])

def _clean_dataframe(df: pd.DataFrame):
    if df is None or df.empty:
        return []
    # Replace NaN, NaT, Inf with None for valid JSON
    df_clean = df.where(pd.notnull(df), None)
    return df_clean.to_dict(orient="records")

@router.get("/reference/listing")
def get_listing():
    """
    Get the full listing of equities (stocks, indices, etc.)
    """
    try:
        ref = Reference()
        df = ref.equity
        if isinstance(df, property) or callable(df):
            # Sometimes .equity is an object with methods. But based on docs, Reference().equity gives dataframe of listing.
            # Let's check docs, docs say: "Reference().equity: Danh sách cổ phiếu, chỉ số, chứng quyền"
            pass
            
        # Actually according to docs: ref.equity returns the Listing Explorer which might need a method call.
        # Wait, the docs say: `Reference().equity` for "Danh sách cổ phiếu".
        # Let's verify by just returning it. If it's a dataframe, clean it.
        # In vnstock_data, `Listing().all_symbols()` was legacy.
        # Let's try `ref.equity.all_symbols()` if it's an object, or if `ref.equity` is a property returning DataFrame.
        # Let's use legacy `from vnstock_data import Listing` for simplicity if Unified UI is tricky, or we can use `Reference().equity.all_symbols()` assuming it's like a namespace.
        # Let me check the documentation of Unified UI I saw earlier.
        
        from vnstock_data import Listing
        lst = Listing()
        df = lst.all_symbols() # legacy method returns a dataframe
        return {"data": _clean_dataframe(df)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/reference/company")
def get_company_profile(symbol: str = Query(..., description="Stock symbol, e.g., TCB")):
    """
    Get company profile information.
    """
    try:
        ref = Reference()
        # docs say: ref.company("TCB").info()
        df = ref.company(symbol.upper()).info()
        return {"data": _clean_dataframe(df)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/market/history")
def get_market_history(symbol: str = Query(..., description="Stock symbol, e.g., TCB"),
                       start: str = Query("2024-01-01", description="Start date YYYY-MM-DD"),
                       end: str = Query("2024-03-01", description="End date YYYY-MM-DD")):
    try:
        mkt = Market()
        df = mkt.equity(symbol.upper()).ohlcv(start=start, end=end)
        return {"data": _clean_dataframe(df)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/fundamental/income-statement")
def get_income_statement(symbol: str = Query(..., description="Stock symbol")):
    try:
        fund = Fundamental()
        df = fund.equity(symbol.upper()).income_statement()
        return {"data": _clean_dataframe(df)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/fundamental/balance-sheet")
def get_balance_sheet(symbol: str = Query(..., description="Stock symbol")):
    try:
        fund = Fundamental()
        df = fund.equity(symbol.upper()).balance_sheet()
        return {"data": _clean_dataframe(df)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ta/indicator")
def get_ta_indicator(symbol: str = Query(..., description="Stock symbol"),
                     indicator: str = Query("RSI", description="Indicator name (RSI, MACD, SMA)"),
                     start: str = Query("2023-01-01", description="Start date for calculation")):
    try:
        # Lấy dữ liệu giá làm đầu vào
        mkt = Market()
        df = mkt.equity(symbol.upper()).ohlcv(start=start)
        
        if df is None or df.empty:
            return {"data": []}
            
        # Format index thành 'time' cho vnstock_ta
        if 'time' in df.columns:
            df = df.set_index('time')
            
        ta = Indicator(data=df)
        
        # Tính toán theo loại chỉ báo
        if indicator.upper() == "RSI":
            result_df = ta.rsi().to_frame()
        elif indicator.upper() == "MACD":
            result_df = ta.macd()
        elif indicator.upper() == "SMA":
            result_df = ta.sma().to_frame()
        else:
            raise ValueError("Indicator not supported in this experiment.")
            
        # Reset index để hiển thị JSON
        result_df = result_df.reset_index()
        
        # Chỉ trả về 50 dòng mới nhất để tránh payload quá lớn
        return {"data": _clean_dataframe(result_df.tail(50))}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/news/latest")
def get_latest_news(site: str = Query("cafef", description="Site config name")):
    try:
        crawler = Crawler(site_name=site)
        articles = crawler.get_articles_from_feed(limit_per_feed=20)
        return {"data": articles}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
