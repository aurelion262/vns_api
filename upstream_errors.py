"""upstream_errors.py — phân loại lỗi quota/rate-limit upstream (tech-spec debt #3).

Routers bọc mọi exception sponsor thành HTTPException(500, detail=str(e));
app-level handler này soi CHUỖI detail theo exhaustion grammar (plan R2 §3.3)
và chỉ khi match mới nâng 429 + X-Upstream-Error: quota — detail giữ nguyên văn.
Mọi HTTPException khác delegate về default chuẩn của FastAPI, nên response shape
của 404/422/500-thường không đổi (verdict R2 §D.2: negatives phải default).

KHÔNG typed matching: type gốc không tới được handler vì routes đã str(e) trước
(verdict R1 F2). KHÔNG Retry-After: chưa có evidence reset-window (verdict R1 F3).
Device/licence exhaustion chưa có signature đáng tin → out-of-scope, fail-open
giữ 500 (plan R2 §3.4).
"""
import re

from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import JSONResponse

# Exhaustion grammar only — bare "quota"/"rate limit" bị loại vì match cả lỗi
# cấu hình/parse/argument (verdict R1 F1; negative matrix tests §4 plan R2).
QUOTA_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"rate limit exceeded",
        r"quota exceeded",
        r"out of quota",
        r"hết lượt",
        r"vượt quá (số )?lượt",
        r"vượt quá giới hạn",
    )
)


def is_upstream_quota_error(detail) -> bool:
    """True khi detail là chuỗi mang tín hiệu cạn/vượt hạn mức. Chỉ nhận str."""
    if not isinstance(detail, str) or not detail:
        return False
    return any(p.search(detail) for p in QUOTA_PATTERNS)


def register_upstream_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def _classify_upstream_quota(request: Request, exc: HTTPException):
        if exc.status_code == 500 and is_upstream_quota_error(exc.detail):
            return JSONResponse(
                status_code=429,
                content={"detail": exc.detail},
                headers={"X-Upstream-Error": "quota"},
            )
        return await http_exception_handler(request, exc)
