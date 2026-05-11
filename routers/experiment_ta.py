from fastapi import APIRouter, HTTPException, Query
import pandas as pd
from vnstock_data import Market
from vnstock_ta import Indicator, Plotter
from pyecharts.globals import CurrentConfig, Locale

# Fix Chinese text in charts
CurrentConfig.LOCALE = Locale.EN


router = APIRouter(prefix="/api/v1/experiment/ta", tags=["Experiment TA"])

def _clean_dataframe(df):
    if df is None:
        return []
    if isinstance(df, pd.DataFrame):
        if df.empty:
            return []
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = ['_'.join(map(str, col)).strip() for col in df.columns.values]
            
        # Include index as a column if it's named 'time' or is DatetimeIndex
        if df.index.name == 'time' or isinstance(df.index, pd.DatetimeIndex):
            df_reset = df.reset_index()
            if 'time' in df_reset.columns:
                df_reset['time'] = df_reset['time'].astype(str)
            df = df_reset
            
        df_clean = df.astype(object).where(pd.notnull(df), None)
        return df_clean.to_dict(orient="records")
    return []

def _process_ta(symbol: str, start: str, end: str, method: str, **kwargs):
    try:
        # 1. Fetch data
        df = Market().equity(symbol).ohlcv(start=start, end=end)
        if df is None or df.empty:
            return {"data": [], "ohlcv_count": 0, "chart": ""}
            
        # 2. Format index for TA
        df = df.set_index('time')
        
        # 3. Calculate indicator
        indicator = Indicator(data=df)
        ind_func = getattr(indicator, method)
        ind_result = ind_func(**kwargs)
        
        # Combine
        if isinstance(ind_result, pd.Series):
            df = df.join(ind_result)
        elif isinstance(ind_result, pd.DataFrame):
            df = df.join(ind_result)
            
        # 4. Generate Chart
        plotter = Plotter(data=df, theme='light', display=False, watermark=False)
        plot_func = getattr(plotter, method)
        
        # Setup title for chart
        title = f"{symbol} - {method.upper()}"
        
        chart = plot_func(**kwargs, title=title)
        
        # Modify DataZoom to allow page scrolling
        if hasattr(chart, 'options') and isinstance(chart.options, dict):
            for dz in chart.options.get("dataZoom", []):
                if isinstance(dz, dict):
                    dz["zoomOnMouseWheel"] = "ctrl"
                    dz["moveOnMouseWheel"] = "shift"
                elif hasattr(dz, 'opts') and isinstance(dz.opts, dict):
                    dz.opts["zoomOnMouseWheel"] = "ctrl"
                    dz.opts["moveOnMouseWheel"] = "shift"
                
        html_str = chart.render_embed()
        
        # Inject script to forward wheel events to parent window if no modifier key is pressed
        js_injection = """
        <script>
          window.addEventListener('wheel', function(e) {
            if (!e.ctrlKey && !e.shiftKey) {
              // Prevent ECharts from capturing the wheel event
              e.stopPropagation();
              // Let the browser handle the native scroll (scrolls the iframe, or bubbles to parent)
            }
          }, { capture: true, passive: false });
        </script>
        </body>
        """
        html_str = html_str.replace("</body>", js_injection)
        
        return {
            "data": _clean_dataframe(df),
            "ohlcv_count": len(df),
            "chart": html_str
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==============================================================================
# TREND INDICATORS (8)
# ==============================================================================

@router.get("/sma")
def get_sma(symbol: str, start: str, end: str, length: int = 14):
    return _process_ta(symbol, start, end, "sma", length=length)

@router.get("/ema")
def get_ema(symbol: str, start: str, end: str, length: int = 14):
    return _process_ta(symbol, start, end, "ema", length=length)

@router.get("/vwap")
def get_vwap(symbol: str, start: str, end: str, anchor: str = "D"):
    return _process_ta(symbol, start, end, "vwap", anchor=anchor)

@router.get("/vwma")
def get_vwma(symbol: str, start: str, end: str, length: int = 20):
    return _process_ta(symbol, start, end, "vwma", length=length)

@router.get("/adx")
def get_adx(symbol: str, start: str, end: str, length: int = 14):
    return _process_ta(symbol, start, end, "adx", length=length)

@router.get("/aroon")
def get_aroon(symbol: str, start: str, end: str, length: int = 14):
    return _process_ta(symbol, start, end, "aroon", length=length)

@router.get("/psar")
def get_psar(symbol: str, start: str, end: str, af0: float = 0.02, af: float = 0.02, max_af: float = 0.2):
    return _process_ta(symbol, start, end, "psar", af0=af0, af=af, max_af=max_af)

@router.get("/supertrend")
def get_supertrend(symbol: str, start: str, end: str, length: int = 10, multiplier: float = 3.0):
    return _process_ta(symbol, start, end, "supertrend", length=length, multiplier=multiplier)

# ==============================================================================
# MOMENTUM INDICATORS (7)
# ==============================================================================

@router.get("/rsi")
def get_rsi(symbol: str, start: str, end: str, length: int = 14):
    return _process_ta(symbol, start, end, "rsi", length=length)

@router.get("/macd")
def get_macd(symbol: str, start: str, end: str, fast: int = 12, slow: int = 26, signal: int = 9):
    return _process_ta(symbol, start, end, "macd", fast=fast, slow=slow, signal=signal)

@router.get("/willr")
def get_willr(symbol: str, start: str, end: str, length: int = 14):
    return _process_ta(symbol, start, end, "willr", length=length)

@router.get("/cmo")
def get_cmo(symbol: str, start: str, end: str, length: int = 9):
    return _process_ta(symbol, start, end, "cmo", length=length)

@router.get("/stoch")
def get_stoch(symbol: str, start: str, end: str, k: int = 14, d: int = 3, smooth_k: int = 3):
    return _process_ta(symbol, start, end, "stoch", k=k, d=d, smooth_k=smooth_k)

@router.get("/roc")
def get_roc(symbol: str, start: str, end: str, length: int = 9):
    return _process_ta(symbol, start, end, "roc", length=length)

@router.get("/mom")
def get_mom(symbol: str, start: str, end: str, length: int = 10):
    return _process_ta(symbol, start, end, "mom", length=length)

# ==============================================================================
# VOLATILITY INDICATORS (5)
# ==============================================================================

@router.get("/bbands")
def get_bbands(symbol: str, start: str, end: str, length: int = 14, std: float = 2.0):
    return _process_ta(symbol, start, end, "bbands", length=length, std=std)

@router.get("/kc")
def get_kc(symbol: str, start: str, end: str, length: int = 20, scalar: float = 2.0, mamode: str = "ema"):
    return _process_ta(symbol, start, end, "kc", length=length, scalar=scalar, mamode=mamode)

@router.get("/atr")
def get_atr(symbol: str, start: str, end: str, length: int = 14):
    return _process_ta(symbol, start, end, "atr", length=length)

@router.get("/stdev")
def get_stdev(symbol: str, start: str, end: str, length: int = 14, ddof: int = 1):
    return _process_ta(symbol, start, end, "stdev", length=length, ddof=ddof)

@router.get("/linreg")
def get_linreg(symbol: str, start: str, end: str, length: int = 14):
    return _process_ta(symbol, start, end, "linreg", length=length)

# ==============================================================================
# VOLUME INDICATORS (1)
# ==============================================================================

@router.get("/obv")
def get_obv(symbol: str, start: str, end: str):
    return _process_ta(symbol, start, end, "obv")
