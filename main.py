from fastapi import FastAPI, Query, HTTPException
from vnstock_data import Market
import pandas as pd
import asyncio
from streamer import AppStreamer

app = FastAPI(title="Vnstock API Server", description="API server for vnstock_data (Paid Version)")

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://engaged-busy-tub-faces.trycloudflare.com", "https://productions-requires-mortgages-far.trycloudflare.com", "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

streamer = AppStreamer()

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

if __name__ == "__main__":
    import uvicorn
    # Chạy tự động tại port 8000, hỗ trợ tự reload khi sửa code
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
