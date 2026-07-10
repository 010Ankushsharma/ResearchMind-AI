"""
main.py

FastAPI application entrypoint.

Wires together:
  - CORS (allowing the Next.js frontend origin)
  - Rate limiting (slowapi)
  - DB lifespan (init on startup, dispose on shutdown)
  - All API routers under settings.API_V1_PREFIX
"""

from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from core.config import settings
from core.request_context import get_request_id, set_request_id
from database.connection import close_db, init_db


class RequestIdLogFilter(logging.Filter):
    """Injects the current request's correlation ID into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id() or "-"
        return True


logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | req=%(request_id)s | %(message)s",
)
# Attached to the HANDLER (not the logger) — a logger-level filter only
# fires for records logged directly on that logger, not ones propagated up
# from child loggers, whereas a handler-level filter fires for every record
# that reaches it regardless of origin.
for _handler in logging.getLogger().handlers:
    _handler.addFilter(RequestIdLogFilter())
logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s (env=%s)", settings.APP_NAME, settings.APP_ENV)
    if settings.APP_ENV == "development":
        # In production, use Alembic migrations instead of create_all.
        await init_db()
        logger.info("Database tables ensured (development mode).")
    yield
    logger.info("Shutting down — disposing DB connections.")
    await close_db()


app = FastAPI(
    title=settings.APP_NAME,
    description="Multi-Agent Research & Report Generation Platform API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# ── Rate Limiting ────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ─────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """
    Generates a correlation ID for every request (or reuses an inbound
    X-Request-ID header, useful if this sits behind a gateway/load balancer
    that already assigns one), stores it in a contextvar so every log line
    emitted while handling this request can be tied back to it, and
    echoes it back in the response for client-side correlation/debugging.
    """
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    set_request_id(request_id)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """
    Baseline security headers for an API service. This app is consumed by
    its own Next.js frontend (not embedded in third-party iframes, and
    cookies aren't used for auth — Clerk JWTs go in the Authorization
    header), so the policy here is intentionally simple rather than a full
    CSP; tighten further if you start serving any HTML directly from this
    service.
    """
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if settings.APP_ENV != "development":
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response


@app.get("/api/health", tags=["health"])
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME, "env": settings.APP_ENV}


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# ── Routers ──────────────────────────────────────────────────────────────
# Imported here (not at module top) to avoid circular imports with models
# that some routers' dependencies touch during app construction.
from api.research import router as research_router  # noqa: E402
from api.report import router as report_router  # noqa: E402
from api.history import router as history_router  # noqa: E402
from api.upload import router as upload_router  # noqa: E402
from api.knowledge import router as knowledge_router  # noqa: E402
from api.agents_status import router as agents_status_router  # noqa: E402
from api.analytics import router as analytics_router  # noqa: E402
from api.auth import router as auth_router  # noqa: E402
from api.settings import router as settings_router  # noqa: E402

app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(research_router, prefix=settings.API_V1_PREFIX)
app.include_router(report_router, prefix=settings.API_V1_PREFIX)
app.include_router(history_router, prefix=settings.API_V1_PREFIX)
app.include_router(upload_router, prefix=settings.API_V1_PREFIX)
app.include_router(knowledge_router, prefix=settings.API_V1_PREFIX)
app.include_router(agents_status_router, prefix=settings.API_V1_PREFIX)
app.include_router(analytics_router, prefix=settings.API_V1_PREFIX)
app.include_router(settings_router, prefix=settings.API_V1_PREFIX)
