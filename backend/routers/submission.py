"""
Backend Router — Submission
==============================

POST /submit — Submit a skill record on-chain (after AI scoring).
POST /submit/async — Submit asynchronously (returns immediately).
"""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from backend.core.contract_service import get_contract_service

logger = logging.getLogger("backend.submission")
router = APIRouter(tags=["Submission"])


class SubmitRequest(BaseModel):
    skill_id: str = Field(..., description="Skill domain (e.g. 'python')")
    score: int = Field(..., ge=0, le=100)
    mode: str = Field(default="ai-graded")
    artifact_hash: Optional[str] = None
    subdomain: Optional[str] = None
    source_type: Optional[str] = None
    source_url: Optional[str] = None


class SubmitResponse(BaseModel):
    success: bool
    transaction_id: str
    skill_id: str
    score: int
    timestamp: int
    artifact_hash: str
    explorer_url: str
    mode: str
    status: str = "confirmed"


class AsyncSubmitResponse(BaseModel):
    success: bool
    transaction_id: str
    skill_id: str
    score: int
    timestamp: int
    artifact_hash: str
    explorer_url: str
    mode: str
    status: str = "submitted"


def confirm_transaction_background(txid: str):
    """Background task to confirm transaction."""
    try:
        from backend.core.algorand_client import get_manager
        manager = get_manager()
        result = manager.wait_for_confirmation(txid, timeout=60.0)
        logger.info("✓ Background confirmation complete for txid: %s, round: %s", 
                   txid, result.get("confirmed-round"))
    except Exception as exc:
        logger.error("Background confirmation failed for txid %s: %s", txid, exc)


@router.post("/submit/async", response_model=AsyncSubmitResponse)
async def submit_record_async(req: SubmitRequest, background_tasks: BackgroundTasks):
    """Submit a skill attestation record on-chain (async - returns immediately)."""
    service = get_contract_service()

    timestamp = int(time.time())
    artifact_hash = req.artifact_hash or hashlib.sha256(
        f"{req.skill_id}:{req.score}:{timestamp}".encode()
    ).hexdigest()

    # Domain encoding: "domain:subdomain" if subdomain present
    domain = req.skill_id
    if req.subdomain:
        domain = f"{req.skill_id}:{req.subdomain}"

    # Submit via contract service (async - no confirmation wait)
    result = service.submit_skill_record_async(
        mode=req.mode,
        domain=domain,
        score=req.score,
        artifact_hash=artifact_hash,
        timestamp=timestamp,
    )

    if not result.success:
        logger.error("Submission failed: %s", result.error)
        raise HTTPException(status_code=502, detail=result.error)

    # Add background task to confirm transaction
    background_tasks.add_task(confirm_transaction_background, result.transaction_id)

    return AsyncSubmitResponse(
        success=True,
        transaction_id=result.transaction_id,
        skill_id=req.skill_id,
        score=req.score,
        timestamp=timestamp,
        artifact_hash=artifact_hash,
        explorer_url=result.explorer_url,
        mode=req.mode,
        status="submitted",
    )


@router.post("/submit", response_model=SubmitResponse)
async def submit_record(req: SubmitRequest):
    """Submit a skill attestation record on-chain."""
    service = get_contract_service()

    timestamp = int(time.time())
    artifact_hash = req.artifact_hash or hashlib.sha256(
        f"{req.skill_id}:{req.score}:{timestamp}".encode()
    ).hexdigest()

    # Domain encoding: "domain:subdomain" if subdomain present
    domain = req.skill_id
    if req.subdomain:
        domain = f"{req.skill_id}:{req.subdomain}"

    # Submit via contract service (handles MBR funding automatically)
    result = service.submit_skill_record(
        mode=req.mode,
        domain=domain,
        score=req.score,
        artifact_hash=artifact_hash,
        timestamp=timestamp,
    )

    if not result.success:
        logger.error("Submission failed: %s", result.error)
        raise HTTPException(status_code=502, detail=result.error)

    return SubmitResponse(
        success=True,
        transaction_id=result.transaction_id,
        skill_id=req.skill_id,
        score=req.score,
        timestamp=timestamp,
        artifact_hash=artifact_hash,
        explorer_url=result.explorer_url,
        mode=req.mode,
        status="confirmed",
    )
