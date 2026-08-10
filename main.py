from fastapi import FastAPI, Query, HTTPException, WebSocket, WebSocketDisconnect
from vnstock_data import Market
import pandas as pd
import asyncio
from streamer import AppStreamer
from routers.experiment import router as experiment_router
from routers.experiment_data_ref import router as experiment_data_ref_router
from routers.experiment_data_market import router as experiment_data_market_router
from routers.experiment_data_fun import router as experiment_data_fun_router
from routers.experiment_data_macro import router as experiment_data_macro_router
from routers.experiment_data_insights import router as experiment_data_insights_router
from routers.experiment_data_analytics import router as experiment_data_analytics_router
from routers.experiment_data_schema import router as experiment_data_schema_router
from routers.experiment_ta import router as experiment_ta_router
from routers.experiment_data_retail import router as experiment_data_retail_router

app = FastAPI(title="Vnstock API Server", description="API server for vnstock_data (Paid Version)")

from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

env_mode = os.environ.get("APP_ENV") or os.environ.get("NODE_ENV")
env_file = f".env.{env_mode}" if env_mode else ".env"
if os.path.exists(env_file):
    load_dotenv(env_file)
else:
    load_dotenv(".env")
cors_origins_env = os.environ.get("CORS_ORIGINS", "")
allow_origins_list = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]
if "http://localhost:5173" not in allow_origins_list:
    allow_origins_list.append("http://localhost:5173")
if "http://localhost:3000" not in allow_origins_list:
    allow_origins_list.append("http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

streamer = AppStreamer()

app.include_router(experiment_router)
app.include_router(experiment_data_ref_router)
app.include_router(experiment_data_market_router)
app.include_router(experiment_data_fun_router)
app.include_router(experiment_data_macro_router)
app.include_router(experiment_data_insights_router)
app.include_router(experiment_data_analytics_router)
app.include_router(experiment_data_schema_router)
app.include_router(experiment_ta_router)
app.include_router(experiment_data_retail_router)
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(streamer.start())

@app.get("/api/v1/quotes")
def get_quotes(symbols: str = Query(..., description="Comma separated list of stock symbols, e.g., TCB,VIC,HPG")):
    try:
        # Parse symbols
        symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
        
        if not symbol_list:
            raise HTTPException(status_code=400, detail="No valid symbols provided.")

        # Khởi tạo mô-đun Market của thư viện vnstock_data (Unified UI)
        mkt = Market()
        
        # Lấy báo giá thị trường (quote) cho nhiều mã cùng lúc
        df_quotes = mkt.quote(symbol_list)
        
        if df_quotes is None or df_quotes.empty:
            return {"data": []}
            
        # Làm sạch dữ liệu: Đổi NaN thành None để API trả về định dạng JSON kiểu null hợp lệ
        df_quotes = df_quotes.where(pd.notnull(df_quotes), None)
        
        # Đóng gói định dạng DataFrame chuyển thành kiểu JSON (list of dicts)
        result = df_quotes.to_dict(orient="records")
        
        return {"data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/streamer/refresh")
def refresh_streamer():
    """Signal the streamer to refresh rules immediately."""
    streamer.force_refresh()
    return {"success": True, "message": "Refresh signal sent"}

@app.get("/streamer/health")
def streamer_health():
    """Check WebSocket streamer health status."""
    return streamer.get_health()

@app.websocket("/ws/prices/{symbol}")
async def ws_prices(websocket: WebSocket, symbol: str):
    """WebSocket realtime cho chart. Push 1m candle updates mỗi tick (market-hours only).
    Client connect → subscribe symbol → nhận candle dict {time,open,high,low,close,volume}."""
    await websocket.accept()
    symbol = symbol.upper()
    # Subscribe upstream + register queue
    streamer.subscribe_chart_symbol(symbol)
    q = streamer.chart_processor.subscribe(symbol)
    # Sol R3: Seed candle ban đầu (nếu trong giờ) — chỉ khi chưa có candle
    # (tránh overwrite candle đang chạy khi subscriber thứ 2 kết nối).
    if symbol not in streamer.chart_processor.candles:
        await streamer.chart_processor.seed_candle(symbol)
    # Push seed candle ngay cho client (tránh wait)
    if symbol in streamer.chart_processor.candles:
        try:
            await websocket.send_json({'type': 'seed', 'candle': streamer.chart_processor.candles[symbol].to_dict()})
        except Exception:
            pass
    try:
        while True:
            # Đợi candle update từ queue (timeout 30s để gửi ping keepalive)
            try:
                candle = await asyncio.wait_for(q.get(), timeout=30)
                await websocket.send_json({'type': 'update', 'candle': candle})
            except asyncio.TimeoutError:
                # Keepalive ping
                await websocket.send_json({'type': 'ping'})
    except WebSocketDisconnect:
        pass
    except Exception as e:
        import logging
        logging.error(f"WS prices {symbol} error: {e}")
    finally:
        # Cleanup
        streamer.chart_processor.unsubscribe(symbol, q)
        # Chỉ unsubscribe upstream nếu không còn subscriber nào cho symbol
        if symbol not in streamer.chart_processor.subscribers:
            streamer.unsubscribe_chart_symbol(symbol)
        try:
            await websocket.close()
        except Exception:
            pass

if __name__ == "__main__":
    import uvicorn
    # Chạy tự động tại port 8000, hỗ trợ tự reload khi sửa code
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

