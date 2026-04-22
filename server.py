"""
High-performance async HTTP server built with FastAPI + Uvicorn.

Features:
  - Fully async request handling via asyncio
  - JSON / plain-text / health endpoints
  - Graceful shutdown
  - Configurable via environment variables

Usage:
  pip install fastapi uvicorn[standard]
  python server.py

Environment variables:
  HOST      - bind address  (default: 0.0.0.0)
  PORT      - bind port     (default: 8000)
  WORKERS   - worker count  (default: 1; use >1 for multi-process)
  LOG_LEVEL - log level     (default: info)
"""

from __future__ import annotations

import os
import time
from contextlib import asynccontextmanager
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse

# ---------------------------------------------------------------------------
# Lifespan – startup / shutdown hooks
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.start_time = time.monotonic()
    print("Server started.")
    yield
    print("Server shutting down.")


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="High-Performance HTTP Server",
    version="1.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Middleware – add X-Response-Time header to every response
# ---------------------------------------------------------------------------

@app.middleware("http")
async def add_response_time(request: Request, call_next):
    t0 = time.monotonic()
    response = await call_next(request)
    elapsed_ms = (time.monotonic() - t0) * 1000
    response.headers["X-Response-Time"] = f"{elapsed_ms:.3f}ms"
    return response


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=PlainTextResponse)
async def root() -> str:
    return "OK"


@app.get("/health", response_class=JSONResponse)
async def health(request: Request) -> dict[str, Any]:
    uptime = time.monotonic() - request.app.state.start_time
    return {"status": "healthy", "uptime_seconds": round(uptime, 2)}


@app.get("/echo", response_class=JSONResponse)
async def echo(request: Request) -> dict[str, Any]:
    return {
        "method": request.method,
        "url": str(request.url),
        "headers": dict(request.headers),
        "query_params": dict(request.query_params),
    }


@app.post("/echo", response_class=JSONResponse)
async def echo_body(request: Request) -> dict[str, Any]:
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            body: Any = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON body")
    else:
        raw = await request.body()
        body = raw.decode(errors="replace")
    return {"body": body}


@app.get("/info", response_class=JSONResponse)
async def info() -> dict[str, Any]:
    import platform
    import sys

    return {
        "python_version": sys.version,
        "platform": platform.platform(),
        "pid": os.getpid(),
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        workers=int(os.getenv("WORKERS", "1")),
        log_level=os.getenv("LOG_LEVEL", "info"),
        # Performance tuning
        loop="uvloop",          # fastest event loop (Linux/macOS); falls back on Windows
        http="httptools",       # fast HTTP parser
        access_log=True,
    )
