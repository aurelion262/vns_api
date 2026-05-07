from fastapi import APIRouter, HTTPException, Query
import pandas as pd
from vnstock_data import Market

router = APIRouter(prefix="/api/v1/experiment/data/market", tags=["Experiment Data Market"])

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

def _parse_kwargs(start, end, interval, limit, timezone):
    kwargs = {}
    if start: kwargs['start'] = start
    if end: kwargs['end'] = end
    if interval: kwargs['interval'] = interval
    if limit: kwargs['limit'] = limit
    if timezone: kwargs['timezone'] = timezone
    return kwargs

# --------------------------------------------------------------------------------
# 1. Equity Market
# --------------------------------------------------------------------------------

@router.get("/equity/ohlcv")
def equity_ohlcv(symbol: str = Query(...), start: str = None, end: str = None):
    try: return {"data": _clean_dataframe(Market().equity(symbol.upper()).ohlcv(**_parse_kwargs(start, end, None, None, None)))}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/equity/trade_history")
def equity_trade_history(symbol: str = Query(...), start: str = None, end: str = None):
    try: return {"data": _clean_dataframe(Market().equity(symbol.upper()).trade_history(**_parse_kwargs(start, end, None, None, None)))}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/equity/trades")
def equity_trades(symbol: str = Query(...)):
    try: return {"data": _clean_dataframe(Market().equity(symbol.upper()).trades())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/equity/order_book")
def equity_order_book(symbol: str = Query(...)):
    try: return {"data": _clean_dataframe(Market().equity(symbol.upper()).order_book())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/equity/quote")
def equity_quote(symbol: str = Query(...)):
    try: return {"data": _clean_dataframe(Market().equity(symbol.upper()).quote())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/equity/session_stats")
def equity_session_stats(symbol: str = Query(...)):
    try: return {"data": _clean_dataframe(Market().equity(symbol.upper()).session_stats())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/equity/foreign_flow")
def equity_foreign_flow(symbol: str = Query(...)):
    try: return {"data": _clean_dataframe(Market().equity(symbol.upper()).foreign_flow())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/equity/proprietary_flow")
def equity_proprietary_flow(symbol: str = Query(...)):
    try: return {"data": _clean_dataframe(Market().equity(symbol.upper()).proprietary_flow())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/equity/block_trades")
def equity_block_trades(symbol: str = Query(...)):
    try: return {"data": _clean_dataframe(Market().equity(symbol.upper()).block_trades())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/equity/odd_lot")
def equity_odd_lot(symbol: str = Query(...)):
    try: return {"data": _clean_dataframe(Market().equity(symbol.upper()).odd_lot())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/equity/volume_profile")
def equity_volume_profile(symbol: str = Query(...)):
    try: return {"data": _clean_dataframe(Market().equity(symbol.upper()).volume_profile())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/equity/summary")
def equity_summary(symbol: str = Query(...)):
    try: return {"data": _clean_dataframe(Market().equity(symbol.upper()).summary())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

# --------------------------------------------------------------------------------
# 2. Index Market
# --------------------------------------------------------------------------------

@router.get("/index/ohlcv")
def index_ohlcv(symbol: str = Query(...), start: str = None, end: str = None):
    try: return {"data": _clean_dataframe(Market().index(symbol.upper()).ohlcv(**_parse_kwargs(start, end, None, None, None)))}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/index/quote")
def index_quote(symbol: str = Query(...)):
    try: return {"data": _clean_dataframe(Market().index(symbol.upper()).quote())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/index/summary")
def index_summary(symbol: str = Query(...)):
    try: return {"data": _clean_dataframe(Market().index(symbol.upper()).summary())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

# --------------------------------------------------------------------------------
# 3. Futures Market
# --------------------------------------------------------------------------------

@router.get("/futures/ohlcv")
def futures_ohlcv(symbol: str = Query(...), start: str = None, end: str = None):
    try: return {"data": _clean_dataframe(Market().futures(symbol.upper()).ohlcv(**_parse_kwargs(start, end, None, None, None)))}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/futures/quote")
def futures_quote(symbol: str = Query(...)):
    try: return {"data": _clean_dataframe(Market().futures(symbol.upper()).quote())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/futures/trades")
def futures_trades(symbol: str = Query(...)):
    try: return {"data": _clean_dataframe(Market().futures(symbol.upper()).trades())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/futures/order_book")
def futures_order_book(symbol: str = Query(...)):
    try: return {"data": _clean_dataframe(Market().futures(symbol.upper()).order_book())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/futures/summary")
def futures_summary(symbol: str = Query(...)):
    try: return {"data": _clean_dataframe(Market().futures(symbol.upper()).summary())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

# --------------------------------------------------------------------------------
# 4. Warrant Market
# --------------------------------------------------------------------------------

@router.get("/warrant/ohlcv")
def warrant_ohlcv(symbol: str = Query(...), start: str = None, end: str = None):
    try: return {"data": _clean_dataframe(Market().warrant(symbol.upper()).ohlcv(**_parse_kwargs(start, end, None, None, None)))}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/warrant/quote")
def warrant_quote(symbol: str = Query(...)):
    try: return {"data": _clean_dataframe(Market().warrant(symbol.upper()).quote())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/warrant/trades")
def warrant_trades(symbol: str = Query(...)):
    try: return {"data": _clean_dataframe(Market().warrant(symbol.upper()).trades())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/warrant/order_book")
def warrant_order_book(symbol: str = Query(...)):
    try: return {"data": _clean_dataframe(Market().warrant(symbol.upper()).order_book())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/warrant/summary")
def warrant_summary(symbol: str = Query(...)):
    try: return {"data": _clean_dataframe(Market().warrant(symbol.upper()).summary())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

# --------------------------------------------------------------------------------
# 5. ETF Market
# --------------------------------------------------------------------------------

@router.get("/etf/ohlcv")
def etf_ohlcv(symbol: str = Query(...), start: str = None, end: str = None):
    try: return {"data": _clean_dataframe(Market().etf(symbol.upper()).ohlcv(**_parse_kwargs(start, end, None, None, None)))}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/etf/quote")
def etf_quote(symbol: str = Query(...)):
    try: return {"data": _clean_dataframe(Market().etf(symbol.upper()).quote())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/etf/trades")
def etf_trades(symbol: str = Query(...)):
    try: return {"data": _clean_dataframe(Market().etf(symbol.upper()).trades())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/etf/order_book")
def etf_order_book(symbol: str = Query(...)):
    try: return {"data": _clean_dataframe(Market().etf(symbol.upper()).order_book())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/etf/session_stats")
def etf_session_stats(symbol: str = Query(...)):
    try: return {"data": _clean_dataframe(Market().etf(symbol.upper()).session_stats())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/etf/foreign_flow")
def etf_foreign_flow(symbol: str = Query(...)):
    try: return {"data": _clean_dataframe(Market().etf(symbol.upper()).foreign_flow())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/etf/proprietary_flow")
def etf_proprietary_flow(symbol: str = Query(...)):
    try: return {"data": _clean_dataframe(Market().etf(symbol.upper()).proprietary_flow())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/etf/block_trades")
def etf_block_trades(symbol: str = Query(...)):
    try: return {"data": _clean_dataframe(Market().etf(symbol.upper()).block_trades())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/etf/odd_lot")
def etf_odd_lot(symbol: str = Query(...)):
    try: return {"data": _clean_dataframe(Market().etf(symbol.upper()).odd_lot())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/etf/volume_profile")
def etf_volume_profile(symbol: str = Query(...)):
    try: return {"data": _clean_dataframe(Market().etf(symbol.upper()).volume_profile())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/etf/summary")
def etf_summary(symbol: str = Query(...)):
    try: return {"data": _clean_dataframe(Market().etf(symbol.upper()).summary())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

# --------------------------------------------------------------------------------
# 6. Fund Market
# --------------------------------------------------------------------------------

@router.get("/fund/history")
def fund_history(symbol: str = Query(...)):
    try: return {"data": _clean_dataframe(Market().fund(symbol.upper()).history())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/fund/top_holding")
def fund_top_holding(symbol: str = Query(...)):
    try: return {"data": _clean_dataframe(Market().fund(symbol.upper()).top_holding())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/fund/industry_holding")
def fund_industry_holding(symbol: str = Query(...)):
    try: return {"data": _clean_dataframe(Market().fund(symbol.upper()).industry_holding())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/fund/asset_holding")
def fund_asset_holding(symbol: str = Query(...)):
    try: return {"data": _clean_dataframe(Market().fund(symbol.upper()).asset_holding())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

# --------------------------------------------------------------------------------
# 7. Quote Multi-symbol
# --------------------------------------------------------------------------------

@router.get("/quote")
def market_wide_quote(symbols: str = Query(..., description="Comma separated symbols")):
    try:
        symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
        return {"data": _clean_dataframe(Market().quote(symbol_list))}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

# --------------------------------------------------------------------------------
# 8. Crypto Market
# --------------------------------------------------------------------------------

@router.get("/crypto/ohlcv")
def crypto_ohlcv(symbol: str = Query(...), interval: str = "1d", limit: int = 500):
    try: return {"data": _clean_dataframe(Market().crypto(symbol.upper()).ohlcv(interval=interval, limit=limit))}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/crypto/quote")
def crypto_quote(symbol: str = Query(...)):
    try: return {"data": _clean_dataframe(Market().crypto(symbol.upper()).quote())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/crypto/intraday")
def crypto_intraday(symbol: str = Query(...)):
    try: return {"data": _clean_dataframe(Market().crypto(symbol.upper()).intraday())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/crypto/order_book")
def crypto_order_book(symbol: str = Query(...), limit: int = 10):
    try: return {"data": _clean_dataframe(Market().crypto(symbol.upper()).order_book(limit=limit))}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/crypto/trade_history")
def crypto_trade_history(symbol: str = Query(...)):
    try: return {"data": _clean_dataframe(Market().crypto(symbol.upper()).trade_history())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/crypto/vwap")
def crypto_vwap(symbol: str = Query(...)):
    try: return {"data": _clean_dataframe(Market().crypto(symbol.upper()).vwap())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/crypto/daily_stats")
def crypto_daily_stats(symbol: str = Query(...)):
    try: return {"data": _clean_dataframe(Market().crypto(symbol.upper()).daily_stats())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/crypto/last_price")
def crypto_last_price(symbol: str = Query(...)):
    try: return {"data": _clean_dataframe(Market().crypto(symbol.upper()).last_price())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/crypto/rolling_stats")
def crypto_rolling_stats(symbol: str = Query(...)):
    try: return {"data": _clean_dataframe(Market().crypto(symbol.upper()).rolling_stats())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/crypto/reference_price")
def crypto_reference_price(symbol: str = Query(...)):
    try: return {"data": _clean_dataframe(Market().crypto(symbol.upper()).reference_price())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

# --------------------------------------------------------------------------------
# 9. Forex & Commodity
# --------------------------------------------------------------------------------

@router.get("/forex/ohlcv")
def forex_ohlcv(symbol: str = Query(...), interval: str = "1d", length: int = 15, timezone: str = None):
    try: return {"data": _clean_dataframe(Market().forex(symbol.upper(), timezone=timezone).ohlcv(interval=interval, length=length))}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/forex/intraday")
def forex_intraday(symbol: str = Query(...), timezone: str = None):
    try: return {"data": _clean_dataframe(Market().forex(symbol.upper(), timezone=timezone).intraday())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/commodity/ohlcv")
def commodity_ohlcv(symbol: str = Query(...), interval: str = "1d", length: int = 15, timezone: str = None):
    try: return {"data": _clean_dataframe(Market().commodity(symbol.upper(), timezone=timezone).ohlcv(interval=interval, length=length))}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/commodity/intraday")
def commodity_intraday(symbol: str = Query(...), timezone: str = None):
    try: return {"data": _clean_dataframe(Market().commodity(symbol.upper(), timezone=timezone).intraday())}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))
