"""FastAPI application assembly — routers, middleware, error handling, lifecycle."""
import hashlib
import logging
import sys
import time
from collections import defaultdict, deque
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import admin, advisor, ai, kyc, office, routes
from app.api import auth as auth_router
from app.core.config import get_settings
from app.core.db import engine, init_db
from app.llm.manager import ProviderManager
from app.models import models  # noqa: F401 — register SQLModel tables

settings = get_settings()

# ---------------------------------------------------------------------------
# Structured JSON logging with request ID + PII masking
# ---------------------------------------------------------------------------
PII_FIELDS = {"gstin", "udyam_number", "phone", "email", "document_name", "business_name"}


class PiiMaskingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        for field in PII_FIELDS:
            import re

            msg = re.sub(
                rf"({field}[\"']?\s*[:=]\s*[\"']?)([^\",}}]+)",
                r"\1***MASKED***",
                msg,
                flags=re.IGNORECASE,
            )
        record.msg = msg
        return True


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return True


logger = logging.getLogger("accel")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter("%(request_id)s %(levelname)s %(name)s %(message)s"))
handler.addFilter(RequestIdFilter())
handler.addFilter(PiiMaskingFilter())
logger.addHandler(handler)


def get_request_id(request: Request) -> str:
    return request.headers.get("x-request-id", f"req-{hashlib.sha256(str(time.time()).encode()).hexdigest()[:8]}")


# ---------------------------------------------------------------------------
# Rate limiting middleware (in-memory, per-IP)
# ---------------------------------------------------------------------------
_rate_limits: dict[str, deque] = defaultdict(deque)


def _rate_limited(ip: str, max_calls: int, window_seconds: int = 60) -> bool:
    now = time.time()
    window = _rate_limits[ip]
    while window and window[0] < now - window_seconds:
        window.popleft()
    if len(window) >= max_calls:
        return True
    window.append(now)
    return False


RATE_LIMITS = {
    "/api/auth/signin": (settings.rate_limit_signin_per_min, 60),
    "/api/auth/signup": (settings.rate_limit_signup_per_min, 60),
    "/api/auth/otp/send": (settings.rate_limit_otp_per_min, 60),
    "/api/auth/otp/verify": (settings.rate_limit_otp_per_min, 60),
    "/api/advisor/message": (settings.rate_limit_advisor_per_min, 60),
    "/api/lookup/": (settings.rate_limit_advisor_per_min, 60),
}


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Accel Business – Udyam Digital",
    version="2.0.0",
    description="API for the Udyam Digital SMB onboarding platform with real authentication and authorization",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Request-ID", "X-CSRF-Token"],
)


@app.middleware("http")
async def rate_limit_and_request_id(request: Request, call_next):
    rid = get_request_id(request)
    ip = request.client.host if request.client else "unknown"

    # Rate limiting
    for path_prefix, (max_calls, window) in RATE_LIMITS.items():
        if request.url.path.startswith(path_prefix):
            if _rate_limited(ip, max_calls, window):
                logger.info("rate_limited", extra={"request_id": rid, "ip": ip, "path": request.url.path})
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "Too many requests",
                        "status_code": 429,
                        "request_id": rid,
                    },
                )
            break

    logger.info("request_start", extra={"request_id": rid, "path": request.url.path, "method": request.method, "ip": ip})
    response = await call_next(request)
    response.headers["X-Request-ID"] = rid
    logger.info("request_end", extra={"request_id": rid, "status": response.status_code})
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail if isinstance(exc.detail, str) else str(exc.detail),
            "status_code": exc.status_code,
            "request_id": get_request_id(request),
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("unhandled", extra={"request_id": get_request_id(request)})
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "request_id": get_request_id(request),
        },
    )


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(auth_router.router, prefix="/api", tags=["auth"])
app.include_router(routes.router, prefix="/api", tags=["routes"])
app.include_router(advisor.router, prefix="/api/advisor", tags=["advisor"])
app.include_router(kyc.router, prefix="/api", tags=["kyc"])
app.include_router(office.router, prefix="/api/office", tags=["office"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(ai.router, prefix="/api/admin/ai", tags=["admin-ai"])


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------
@app.on_event("startup")
def on_startup():
    init_db()
    try:
        from app.scripts.seed import seed
        seed()
    except Exception as e:
        logger.warning("seed_skipped", extra={"request_id": "-", "error": str(e)})


@app.get("/", tags=["meta"])
def root():
    return {"message": "Accel Business API – Udyam Digital", "docs": "/docs"}


@app.get("/health", response_model=dict[str, Any], tags=["meta"])
def health():
    db = "sqlite" if str(engine.url).startswith("sqlite") else "postgres"
    result: dict[str, Any] = {"status": "ok", "database": db}
    # Add LLM provider health
    try:
        manager = ProviderManager()
        health_results = manager.health_check_all()
        result["llm"] = {
            name: {"healthy": r.healthy, "latency_ms": r.latency_ms, "error": r.error, "model": r.model}
            for name, r in health_results.items()
        }
        result["active_provider"] = manager.active_provider
    except Exception as e:
        result["llm"] = {"error": str(e)}
        result["active_provider"] = "offline"
    return result


@app.get("/ready", response_model=dict[str, Any], tags=["meta"])
def ready():
    from sqlmodel import text
    try:
        with Session(engine) as session:
            session.exec(text("SELECT 1"))
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        return JSONResponse(status_code=503, content={"status": "not_ready", "database": str(e)})


from sqlmodel import Session  # noqa: E402
