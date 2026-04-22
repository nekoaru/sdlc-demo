"""
High-performance async HTTP server built with FastAPI + Uvicorn.

Features:
  - Fully async request handling via Python asyncio
  - JSON / plain-text / health endpoints
  - Graceful shutdown (SIGINT / SIGTERM)
  - Configurable via environment variables
  - X-Response-Time header on every response

Usage:
  pip install -r requirements.txt
  python server.py

Environment variables:
  HOST      - bind address  (default: 0.0.0.0)
  PORT      - bind port     (default: 8000)
  LOG_LEVEL - log level     (default: info)
"""

import os
import platform
import signal
import sys
import time
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", 8000))
LOG_LEVEL = os.environ.get("LOG_LEVEL", "info").lower()

start_time = time.time()

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(lifespan=lifespan)

# ---------------------------------------------------------------------------
# Middleware – add X-Response-Time to every response
# ---------------------------------------------------------------------------

class ResponseTimeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        ts = time.time()
        response = await call_next(request)
        elapsed_ms = int((time.time() - ts) * 1000)
        response.headers["X-Response-Time"] = f"{elapsed_ms}ms"
        return response

app.add_middleware(ResponseTimeMiddleware)

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=PlainTextResponse)
async def root():
    return "OK"


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "uptime_seconds": round(time.time() - start_time),
    }


@app.get("/echo")
async def echo_get(request: Request):
    return {
        "method": request.method,
        "url": str(request.url),
        "headers": dict(request.headers),
        "query_params": dict(request.query_params),
    }


@app.post("/echo")
async def echo_post(request: Request):
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body = await request.json()
    else:
        raw = await request.body()
        body = raw.decode("utf-8", errors="replace")
    return {"body": body}


@app.get("/info")
async def info():
    return {
        "python_version": sys.version,
        "platform": f"{platform.system()} {platform.release()} {platform.machine()}",
        "pid": os.getpid(),
    }

# ---------------------------------------------------------------------------
# Graceful shutdown
# ---------------------------------------------------------------------------

def handle_signal(sig, frame):
    print(f"\nReceived signal {sig}. Shutting down…", flush=True)
    sys.exit(0)

signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)

# ---------------------------------------------------------------------------
# Start
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
        log_level=LOG_LEVEL,
    )
