from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/experiment", tags=["Experiment"])

@router.get("/data/test")
def test_data():
    return {"module": "vnstock_data", "status": "scaffolded"}

@router.get("/ta/test")
def test_ta():
    return {"module": "vnstock_ta", "status": "scaffolded"}

@router.get("/news/test")
def test_news():
    return {"module": "vnstock_news", "status": "scaffolded"}

@router.get("/pipeline/test")
def test_pipeline():
    return {"module": "vnstock_pipeline", "status": "scaffolded"}

@router.get("/chart/test")
def test_chart():
    return {"module": "vnstock_chart", "status": "scaffolded"}
