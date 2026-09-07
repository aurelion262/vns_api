"""Handler tests — register_upstream_error_handlers (plan R2 §4.2).

Mini-app dùng ĐÚNG hàm registration production; real-app test qua main (conftest
stub sponsor). Khóa: canonical quota → 429 + X-Upstream-Error + KHÔNG Retry-After
(verdict R1 F3) + detail nguyên văn; adversarial negatives giữ default 500 shape;
404 delegate default.
"""
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from unittest.mock import patch

from upstream_errors import register_upstream_error_handlers


def make_mini_app() -> FastAPI:
    app = FastAPI()
    register_upstream_error_handlers(app)  # production registration

    @app.get("/q")
    def q():
        raise HTTPException(status_code=500, detail="Rate limit exceeded for provider 'vci'")

    @app.get("/b")
    def b():
        raise HTTPException(status_code=500, detail="boom")

    @app.get("/n1")
    def n1():
        raise HTTPException(status_code=500, detail="quota configuration missing")

    return app


client = TestClient(make_mini_app())


def test_quota_500_becomes_429_with_header_no_retry_after():
    r = client.get("/q")
    assert r.status_code == 429
    assert r.json() == {"detail": "Rate limit exceeded for provider 'vci'"}
    assert r.headers.get("x-upstream-error") == "quota"
    assert "retry-after" not in r.headers  # verdict R1 F3 — header VẮNG


def test_plain_500_keeps_default_shape():
    r = client.get("/b")
    assert r.status_code == 500
    assert r.json() == {"detail": "boom"}
    assert "x-upstream-error" not in r.headers
    assert "retry-after" not in r.headers


def test_marker_non_exhaustion_keeps_default_500():
    r = client.get("/n1")
    assert r.status_code == 500
    assert r.json() == {"detail": "quota configuration missing"}
    assert "x-upstream-error" not in r.headers


def test_404_delegates_default():
    r = client.get("/nope")
    assert r.status_code == 404
    assert r.json() == {"detail": "Not Found"}


# --- Real-app (main wiring) — RED trước khi wire main.py, GREEN sau ---

def _real_app():
    import main  # conftest đã stub sponsor modules
    return TestClient(main.app)


def test_real_app_quota_route_429():
    with patch("routers.experiment_data_market.Market") as MockMarket:
        MockMarket.return_value.equity.return_value.quote.side_effect = Exception(
            "Rate limit exceeded for provider 'vci'"
        )
        r = _real_app().get("/api/v1/experiment/data/market/equity/quote?symbol=VCB")
        assert r.status_code == 429
        assert r.json() == {"detail": "Rate limit exceeded for provider 'vci'"}
        assert r.headers.get("x-upstream-error") == "quota"
        assert "retry-after" not in r.headers


def test_real_app_non_quota_route_keeps_500():
    with patch("routers.experiment_data_market.Market") as MockMarket:
        MockMarket.return_value.equity.return_value.quote.side_effect = ValueError(
            "quota configuration missing"
        )
        r = _real_app().get("/api/v1/experiment/data/market/equity/quote?symbol=VCB")
        assert r.status_code == 500
        assert r.json() == {"detail": "quota configuration missing"}
        assert "x-upstream-error" not in r.headers
