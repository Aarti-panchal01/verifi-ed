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
    reputation: Optional[ReputationResponse] = None


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

        rep = ReputationResponse(
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

        return VerifyWalletResponse(
            wallet=wallet,
            verified=profile.verification_badge,
            record_count=len(result.records),
            records=result.records,
            message=f"{'✅ Verified' if profile.verification_badge else '⚠ Not yet verified'} — {profile.credibility_level.value} credibility ({profile.total_reputation:.0f}/100) with {len(result.records)} on-chain record(s).",
            reputation=rep,
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
    """Retrieve featured talent profiles (Explorer)."""
    # Note: Comprehensive on-chain discovery is slow.
    # We use a set of featured/recent wallets or return a specific list.
    featured_wallets = [
        "IE6HFCN4AEBX3ZSHP7NOCVC54F7BKSEATB2AXXGYI3YU2GWQHK5IMCKUA", # Example
        "A7MZ4O2B5M... (example)",
    ]
    
    # In a real app with a DB, we would query the index.
    # For now, we'll return a mocked list of potential profiles or the requested wallet if provided in 'q'.
    
    profiles = []
    service = get_contract_service()
    
    # If user searched for a specific wallet
    wallets_to_check = [q] if q and len(q) >= 58 else featured_wallets[:limit]
    
    for w in wallets_to_check:
        try:
            result = service.get_skill_records(w)
            if result.success and result.records:
                profile = rep_engine.compute(w, result.records)
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
        except Exception:
            continue

    # Filter by domain if requested
    if domain:
        profiles = [p for p in profiles if p.get("top_domain") == domain or any(ds["domain"] == domain for ds in p.get("domain_scores", []))]

    return {"profiles": profiles}
