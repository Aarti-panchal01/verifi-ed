"""
Backend Router — Verification
===============================

POST /verify-evidence/repo              — Verify a GitHub repo
POST /verify-evidence/certificate/upload — Verify a certificate file
POST /verify-evidence/project/upload     — Verify a project archive (ZIP)
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import tempfile
import json
import time
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from pathlib import Path as FSPath

from ai_scoring.github_analyzer import GitHubAnalyzer
from verification_engine.certificate_verifier import CertificateVerifier
from verification_engine.project_verifier import ProjectVerifier

logger = logging.getLogger("backend.verification")
router = APIRouter(prefix="/verify-evidence", tags=["Verification"])

github_analyzer = GitHubAnalyzer()
cert_v = CertificateVerifier()
project_v = ProjectVerifier()

# region agent log
_AGENT_DEBUG_LOG_PATH = FSPath(
    r"c:\Users\Aarti Panchal\Downloads\verifi.ed-main\verifi.ed\.cursor\debug.log"
)


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
        pass

# endregion agent log


class RepoVerifyRequest(BaseModel):
    repo_url: str
    wallet: Optional[str] = None
    mode: str = "developer"


class VerificationResponse(BaseModel):
    verified: bool
    overall_score: float
    source_type: str
    signals: list[dict] = []
    domains: list[dict] = []
    metadata: dict = {}
    error: Optional[str] = None


@router.post("/repo", response_model=VerificationResponse)
async def verify_repo(req: RepoVerifyRequest):
    """Verify and analyze a GitHub repository using the fast GitHubAnalyzer."""
    try:
        _agent_log(
            hypothesisId="H-verify-repo",
            runId="pre-fix",
            location="backend/routers/verification.py:verify_repo",
            message="verify_repo entry.",
            data={"repo_url_len": len(req.repo_url or ""), "wallet_present": bool(req.wallet), "mode": req.mode},
        )

        # Use the fast GitHubAnalyzer directly (parallel fetching + cache)
        result = await github_analyzer.analyze(req.repo_url)

        if result.get("metadata", {}).get("error"):
            return VerificationResponse(
                verified=False,
                overall_score=0.0,
                source_type="github-repo",
                error=result["metadata"]["error"],
            )

        score = result.get("overall_score", 0.0)

        return VerificationResponse(
            verified=score >= 0.4,
            overall_score=score,
            source_type="github-repo",
            signals=[
                {
                    "signal_name": s.signal_name,
                    "value": s.value,
                    "max_value": s.max_value,
                    "normalized": s.normalized,
                    "detail": s.detail,
                }
                for s in result.get("signals", [])
            ],
            domains=[
                {
                    "domain": d.domain,
                    "confidence": d.confidence,
                }
                for d in result.get("domains", [])
            ],
            metadata=result.get("metadata", {}),
        )
    except Exception as exc:
        logger.error("Repo verification failed: %s", exc, exc_info=True)
        _agent_log(
            hypothesisId="H-verify-repo",
            runId="pre-fix",
            location="backend/routers/verification.py:verify_repo",
            message="verify_repo exception.",
            data={"error_type": type(exc).__name__, "error": str(exc)[:300]},
        )
        raise HTTPException(status_code=502, detail=str(exc))


@router.post("/certificate/upload", response_model=VerificationResponse)
async def verify_certificate_upload(
    file: UploadFile = File(...),
    mode: str = Form("learner")
):
    """Verify an uploaded certificate file (PDF, PNG, JPG)."""
    temp_path = None
    try:
        _agent_log(
            hypothesisId="H-verify-certificate",
            runId="pre-fix",
            location="backend/routers/verification.py:verify_certificate_upload",
            message="verify_certificate_upload entry.",
            data={"filename": file.filename, "mode": mode},
        )
        suffix = os.path.splitext(file.filename or "file")[1] or ".bin"
        # Create temp file but close it immediately so it can be re-opened by verifier on Windows
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            temp_path = tmp.name
        # File is effectively closed here by __exit__


        logger.info("Processing certificate: %s (%d bytes)", file.filename, len(content))

        result = await cert_v.verify(temp_path)

        return VerificationResponse(
            verified=result.verified,
            overall_score=result.overall_score,
            source_type=result.source_type.value,
            signals=[s.model_dump() for s in result.signals],
            domains=[d.model_dump() for d in result.domains_detected],
            metadata={
                **result.metadata,
                "original_filename": file.filename,
                "artifact_hash": result.metadata.get("sha256", ""),
            },
            error=result.error,
        )
    except Exception as exc:
        logger.error("Certificate verification failed: %s", exc, exc_info=True)
        _agent_log(
            hypothesisId="H-verify-certificate",
            runId="pre-fix",
            location="backend/routers/verification.py:verify_certificate_upload",
            message="verify_certificate_upload exception.",
            data={"error_type": type(exc).__name__, "error": str(exc)[:300]},
        )
        raise HTTPException(status_code=502, detail=str(exc))
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


@router.post("/project/upload", response_model=VerificationResponse)
async def verify_project_upload(
    file: UploadFile = File(...),
    mode: str = Form("developer")
):
    """Verify an uploaded project archive (ZIP/TAR)."""
    temp_dir = None
    try:
        _agent_log(
            hypothesisId="H-verify-project",
            runId="pre-fix",
            location="backend/routers/verification.py:verify_project_upload",
            message="verify_project_upload entry.",
            data={"filename": file.filename, "mode": mode},
        )
        temp_dir = tempfile.mkdtemp()
        archive_path = os.path.join(temp_dir, file.filename or "project.zip")

        content = await file.read()
        with open(archive_path, "wb") as f:
            f.write(content)

        logger.info("Processing project archive: %s (%d bytes)", file.filename, len(content))

        # Extract
        extract_path = os.path.join(temp_dir, "extracted")
        os.makedirs(extract_path, exist_ok=True)

        try:
            shutil.unpack_archive(archive_path, extract_path)
        except Exception as e:
            logger.warning("Archive extraction failed: %s", e)
            raise HTTPException(
                status_code=400,
                detail=f"Could not extract archive: {e}. Please upload a valid ZIP/TAR file."
            )

        # Check for single top-level folder (common in ZIP exports)
        extracted_items = os.listdir(extract_path)
        if len(extracted_items) == 1:
            single_dir = os.path.join(extract_path, extracted_items[0])
            if os.path.isdir(single_dir):
                extract_path = single_dir

        result = await project_v.verify(extract_path)

        return VerificationResponse(
            verified=result.verified,
            overall_score=result.overall_score,
            source_type=result.source_type.value,
            signals=[s.model_dump() for s in result.signals],
            domains=[d.model_dump() for d in result.domains_detected],
            metadata={
                **result.metadata,
                "original_filename": file.filename,
                "artifact_hash": result.metadata.get("project_hash", ""),
            },
            error=result.error,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Project verification failed: %s", exc, exc_info=True)
        _agent_log(
            hypothesisId="H-verify-project",
            runId="pre-fix",
            location="backend/routers/verification.py:verify_project_upload",
            message="verify_project_upload exception.",
            data={"error_type": type(exc).__name__, "error": str(exc)[:300]},
        )
        raise HTTPException(status_code=502, detail=str(exc))
    finally:
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass
