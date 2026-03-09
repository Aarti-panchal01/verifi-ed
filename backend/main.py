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

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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
    allow_origins=["*"],
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
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()

    if client_ip not in _rate_store:
        _rate_store[client_ip] = []

    # Clean old entries
    _rate_store[client_ip] = [t for t in _rate_store[client_ip] if now - t < RATE_WINDOW]

    if len(_rate_store[client_ip]) >= RATE_LIMIT:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded. Try again later."},
        )

    _rate_store[client_ip].append(now)
    return await call_next(request)


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


@app.get("/health", tags=["Info"])
async def health():
    return {"status": "healthy", "timestamp": int(time.time())}

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
