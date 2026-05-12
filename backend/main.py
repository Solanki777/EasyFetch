"""FastAPI application entry point."""
from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api.routes import chat, session, health
from backend.config import settings
from backend.session.manager import SessionManager
from backend.utils.logging_config import setup_logging

# Initialise structured logging before anything else
setup_logging()
logger = logging.getLogger(__name__)


# ── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown logic."""
    logger.info("Drive Assistant API starting", extra={"version": settings.app_version})
    app.state.session_manager = SessionManager(ttl_seconds=settings.session_ttl_seconds)
    yield
    logger.info("Drive Assistant API shutting down")


# ── App factory ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="Drive Assistant API",
    description="Conversational AI Google Drive File Discovery Assistant",
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request tracing middleware ────────────────────────────────────────────────

@app.middleware("http")
async def request_tracing_middleware(request: Request, call_next):
    # High-visibility print to bypass any logging issues
    print(f"\n>>> Incoming Request: {request.method} {request.url.path}", flush=True)

    request_id = str(uuid.uuid4())[:8]
    start = time.perf_counter()
    request.state.request_id = request_id

    logger.info(
        "Request started",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
        },
    )

    try:
        response = await call_next(request)
    except Exception as exc:
        logger.exception("Unhandled exception in middleware", extra={"request_id": request_id})
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    elapsed_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "Request completed",
        extra={
            "request_id": request_id,
            "status_code": response.status_code,
            "latency_ms": round(elapsed_ms, 2),
        },
    )
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Latency-MS"] = str(round(elapsed_ms, 2))
    return response


# ── Routes ────────────────────────────────────────────────────────────────────

app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
app.include_router(session.router, prefix="/api/v1", tags=["session"])
app.include_router(health.router, tags=["health"])
