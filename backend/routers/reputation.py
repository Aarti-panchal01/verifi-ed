"""
Backend Router — Reputation
==============================

GET /reputation/{wallet} — Compute reputation profile
GET /verify/{wallet}     — On-chain verification status
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.core.contract_service import get_contract_service
from reputation_engine.engine import ReputationEngine

logger = logging.getLogger("backend.reputation")
router = APIRouter(tags=["Reputation"])

rep_engine = ReputationEngine()


class DomainScoreResponse(BaseModel):
    domain: str
    score: float
    record_count: int
    latest_timestamp: int
    trend: str


class ReputationResponse(BaseModel):
    wallet: str
    total_reputation: float
    credibility_level: str
    trust_index: float
    verification_badge: bool
    total_records: int
    top_domain: Optional[str] = None
    active_since: Optional[int] = None
    domain_scores: list[DomainScoreResponse] = []


class VerifyWalletResponse(BaseModel):
    wallet: str
    verified: bool
    record_count: int
    records: list[dict]
    message: str
    # Flattened reputation fields for frontend consistency
    total_reputation: float = 0.0
    credibility_level: str = "minimal"
    trust_index: float = 0.0
    top_domain: Optional[str] = None
    domain_scores: list[DomainScoreResponse] = []


@router.get("/reputation/{wallet}", response_model=ReputationResponse)
async def get_reputation(wallet: str):
    """Compute full reputation profile for a wallet."""
    try:
        service = get_contract_service()
        result = service.get_skill_records(wallet)

        if not result.success:
            raise HTTPException(status_code=502, detail=result.error)

        profile = rep_engine.compute(wallet, result.records)

        return ReputationResponse(
            wallet=profile.wallet,
            total_reputation=profile.total_reputation,
            credibility_level=profile.credibility_level.value,
            trust_index=profile.trust_index,
            verification_badge=profile.verification_badge,
            total_records=profile.total_records,
            top_domain=profile.top_domain,
            active_since=profile.active_since,
            domain_scores=[
                DomainScoreResponse(
                    domain=ds.domain,
                    score=ds.score,
                    record_count=ds.record_count,
                    latest_timestamp=ds.latest_timestamp,
                    trend=ds.trend,
                )
                for ds in profile.domain_scores
            ],
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Reputation failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=502, detail=str(exc))


@router.get("/verify/{wallet}", response_model=VerifyWalletResponse)
async def verify_wallet(wallet: str):
    """Verify a wallet's on-chain records + reputation."""
    try:
        service = get_contract_service()
        result = service.get_skill_records(wallet)

        if not result.success:
            raise HTTPException(status_code=502, detail=result.error)

        if not result.records:
            return VerifyWalletResponse(
                wallet=wallet,
                verified=False,
                record_count=0,
                records=[],
                message="No skill records found for this wallet.",
            )

        profile = rep_engine.compute(wallet, result.records)

        return VerifyWalletResponse(
            wallet=wallet,
            verified=profile.verification_badge,
            record_count=len(result.records),
            records=result.records,
            message=f"{'✅ Verified' if profile.verification_badge else '⚠ Not yet verified'} — {profile.credibility_level.value} credibility ({profile.total_reputation:.0f}/100) with {len(result.records)} on-chain record(s).",
            total_reputation=profile.total_reputation,
            credibility_level=profile.credibility_level.value,
            trust_index=profile.trust_index,
            top_domain=profile.top_domain,
            domain_scores=[
                DomainScoreResponse(
                    domain=ds.domain,
                    score=ds.score,
                    record_count=ds.record_count,
                    latest_timestamp=ds.latest_timestamp,
                    trend=ds.trend,
                )
                for ds in profile.domain_scores
            ],
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Verify failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=502, detail=str(exc))


@router.get("/reputation/explore")
async def explore_talents(
    q: Optional[str] = None,
    domain: Optional[str] = None,
    limit: int = 20
):
    """Retrieve talent profiles (Explorer)."""
    # Active wallets on TestNet (for demonstration)
    featured_wallets = [
        "IE6HFCN4AEBX3ZSHP7NOCVC54F7BKSEATB2AXXGYI3YU2GWQHK5IMCKUA",
        "W4L6ALX6E6A2Z2B2C2D2E2F2G2H2I2J2K2L2M2N2O2P2Q2R2S2T2U2V", # Mock valid length
    ]
    
    profiles = []
    service = get_contract_service()
    
    # Prioritize search query if provided
    wallets_to_check = []
    if q and len(q) >= 58:
        wallets_to_check.append(q)
    
    # Fill with featured wallets
    for w in featured_wallets:
        if w not in wallets_to_check:
            wallets_to_check.append(w)
            
    wallets_to_check = wallets_to_check[:limit]
    
    for w in wallets_to_check:
        try:
            # Check for valid address format first
            if len(w) < 58: continue
            
            result = service.get_skill_records(w)
            if result.success and result.records:
                profile = rep_engine.compute(w, result.records)
                
                # Domain filter logic
                if domain:
                    match = (profile.top_domain == domain) or any(ds.domain == domain for ds in profile.domain_scores)
                    if not match: continue

                profiles.append({
                    "wallet": w,
                    "total_reputation": profile.total_reputation,
                    "credibility_level": profile.credibility_level.value,
                    "trust_index": profile.trust_index,
                    "verification_badge": profile.verification_badge,
                    "total_records": profile.total_records,
                    "top_domain": profile.top_domain,
                    "domain_scores": [
                        {"domain": ds.domain, "score": ds.score}
                        for ds in profile.domain_scores
                    ]
                })
        except Exception as e:
            logger.debug("Explorer lookup failed for %s: %s", w, e)
            continue

    return {"profiles": profiles}
