"""
Verified Protocol — Backend API
==================================

Production-ready FastAPI application for the Decentralized Skill
Reputation Protocol. Routes through modular routers for:

    • /analyze/*       — AI-powered evidence scoring
    • /verify-evidence/* — Evidence verification pipeline
    • /submit          — On-chain skill record submission
    • /wallet/*        — Record retrieval
    • /timeline/*      — Chronological record timeline
    • /reputation/*    — Aggregated reputation profiles
    • /verify/*        — Wallet on-chain verification
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# region agent log
import json
from pathlib import Path

_AGENT_DEBUG_LOG_PATH = Path(r"c:\Users\Aarti Panchal\Downloads\verifi.ed-main\verifi.ed\.cursor\debug.log")


def _agent_log(*, hypothesisId: str, runId: str, location: str, message: str, data: dict) -> None:
    try:
        _AGENT_DEBUG_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        _AGENT_DEBUG_LOG_PATH.open("a", encoding="utf-8").write(
            json.dumps(
                {
                    "id": f"log_{int(time.time() * 1000)}_{hypothesisId}",
                    "timestamp": int(time.time() * 1000),
                    "hypothesisId": hypothesisId,
                    "runId": runId,
                    "location": location,
                    "message": message,
                    "data": data,
                },
                ensure_ascii=False,
            )
            + "\n"
        )
    except Exception:
        # Never let debug logging break production paths
        pass

# endregion agent log

# ─────────────────────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("verified_protocol")


# ─────────────────────────────────────────────────────────────────────────────
# Lifespan
# ─────────────────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Verified Protocol API starting…")
    # region agent log
    _agent_log(
        hypothesisId="H-startup-env",
        runId="pre-fix",
        location="backend/main.py:lifespan",
        message="API starting; key env presence (no values).",
        data={
            "has_ALGOD_SERVER": bool(__import__("os").getenv("ALGOD_SERVER")),
            "has_INDEXER_SERVER": bool(__import__("os").getenv("INDEXER_SERVER")),
            "has_DEPLOYER_MNEMONIC": bool(__import__("os").getenv("DEPLOYER_MNEMONIC")),
            "has_DEPLOYER": bool(__import__("os").getenv("DEPLOYER")),
            "has_PORT": bool(__import__("os").getenv("PORT")),
        },
    )
    # endregion agent log
    yield
    logger.info("🛑 Verified Protocol API shutting down…")


# ─────────────────────────────────────────────────────────────────────────────
# App
# ─────────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Verified Protocol — Skill Reputation API",
    description=(
        "Decentralized Skill Reputation Layer for AI-Verified Talent. "
        "Analyze evidence, verify credentials, submit on-chain attestations, "
        "and query aggregated reputation profiles."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*", 
        "https://verifi-ed.vercel.app",
        "https://verifi-ed-production.up.railway.app"
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request timing middleware ─────────────────────────────────────────
@app.middleware("http")
async def timing_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start
    response.headers["X-Process-Time-Ms"] = f"{elapsed * 1000:.1f}"
    logger.info(
        "%s %s — %d — %.1fms",
        request.method, request.url.path,
        response.status_code, elapsed * 1000,
    )
    return response


# ── Rate limiting (simple in-memory) ─────────────────────────────────
_rate_store: dict[str, list[float]] = {}
RATE_LIMIT = 60  # requests per minute
RATE_WINDOW = 60  # seconds


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # Disable rate limit for health check
    if request.url.path == "/health":
        return await call_next(request)
        
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()

    # region agent log
    _agent_log(
        hypothesisId="H-cors-proxy-ip",
        runId="pre-fix",
        location="backend/main.py:rate_limit_middleware",
        message="Request metadata for CORS/proxy/IP debugging.",
        data={
            "path": request.url.path,
            "method": request.method,
            "origin": request.headers.get("origin"),
            "host": request.headers.get("host"),
            "x_forwarded_for_present": bool(request.headers.get("x-forwarded-for")),
            "x_forwarded_proto": request.headers.get("x-forwarded-proto"),
            "client_ip_seen": client_ip,
        },
    )
    # endregion agent log
    
    if client_ip not in _rate_store:
        _rate_store[client_ip] = []
    
    # Clean old entries
    _rate_store[client_ip] = [t for t in _rate_store[client_ip] if now - t < RATE_WINDOW]
    
    # If we are in production behind a proxy, we might need X-Forwarded-For
    # For now, let's keep it simple but generous
    if len(_rate_store[client_ip]) >= (RATE_LIMIT * 2): # Double the limit in prod
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many requests. Please slow down."},
        )
    
    _rate_store[client_ip].append(now)
    return await call_next(request)

# region agent log
@app.middleware("http")
async def agent_exception_logger(request: Request, call_next):
    """Debug-only: log exceptions into debug.log for runtime evidence."""
    try:
        return await call_next(request)
    except Exception as exc:
        _agent_log(
            hypothesisId="H-unhandled-exception",
            runId="pre-fix",
            location="backend/main.py:agent_exception_logger",
            message="Unhandled exception in request pipeline.",
            data={
                "path": request.url.path,
                "method": request.method,
                "error_type": type(exc).__name__,
                "error": str(exc)[:500],
            },
        )
        raise
# endregion agent log

@app.get("/health", tags=["System"])
async def health():
    return {"status": "ok", "time": time.time()}

# region agent log
@app.get("/__agent_debug/ping", tags=["System"])
async def agent_debug_ping():
    """Debug-only endpoint to verify NDJSON logging is working."""
    _agent_log(
        hypothesisId="H-log-pipeline",
        runId="pre-fix",
        location="backend/main.py:/__agent_debug/ping",
        message="Ping to validate debug log pipeline.",
        data={"ok": True},
    )
    return {"ok": True}
# endregion agent log


# ── Import & register routers ────────────────────────────────────────
from backend.routers.scoring import router as scoring_router
from backend.routers.verification import router as verification_router
from backend.routers.submission import router as submission_router
from backend.routers.retrieval import router as retrieval_router
from backend.routers.reputation import router as reputation_router

app.include_router(scoring_router)
app.include_router(verification_router)
app.include_router(submission_router)
app.include_router(retrieval_router)
app.include_router(reputation_router)


# ── Root endpoint ─────────────────────────────────────────────────────
@app.get("/", tags=["Info"])
async def root():
    return {
        "protocol": "Verified Protocol",
        "version": "2.0.0",
        "description": "Decentralized Skill Reputation Layer for AI-Verified Talent",
        "network": "algorand-testnet",
        "endpoints": {
            "scoring": [
                "POST /analyze/repo",
                "POST /analyze/certificate",
                "POST /analyze/project",
            ],
            "verification": [
                "POST /verify-evidence/repo",
                "POST /verify-evidence/certificate",
                "POST /verify-evidence/project",
            ],
            "submission": [
                "POST /submit",
            ],
            "retrieval": [
                "GET /wallet/{wallet}",
                "GET /timeline/{wallet}",
            ],
            "reputation": [
                "GET /reputation/{wallet}",
                "GET /verify/{wallet}",
            ],
        },
        "docs": "/docs",
    }

