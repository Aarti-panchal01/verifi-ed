"""
Verified Protocol — Interaction Script
========================================

Production-ready CLI for interacting with the deployed VerifiedProtocol
smart contract on Algorand Testnet (App ID: 755779875).

Usage:
    poetry run python interact.py submit <skill_id> <score> --artifact <file>

    poetry run python interact.py submit <skill_id> <score>
    poetry run python interact.py verify <skill_id>

Environment:
    Reads .env for ALGOD_SERVER, ALGOD_PORT, ALGOD_TOKEN, and DEPLOYER_MNEMONIC.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

from hash_artifact import hash_file, hash_string

from backend.core.algorand_client import get_manager
from backend.core.arc4_decoder import ARC4Decoder
from backend.core.contract_service import get_contract_service

# ─────────────────────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("verified_protocol")


# ─────────────────────────────────────────────────────────────────────────────
# Initialize services
# ─────────────────────────────────────────────────────────────────────────────
def _init_services():
    """Initialize Algorand manager and contract service."""
    env_path = Path(__file__).parent / ".env"
    manager = get_manager(env_path)
    service = get_contract_service()
    
    logger.info("Deployer address : %s", manager.deployer_address)
    logger.info("Connected to app : %d", service.app_id)
    logger.info("App address      : %s", service.client.app_address)
    
    return manager, service


# ─────────────────────────────────────────────────────────────────────────────
# Core actions
# ─────────────────────────────────────────────────────────────────────────────
def submit_skill_record(skill_id: str, score: int, artifact_path: str | None = None) -> None:
    """Submit a new skill attestation record to the on-chain ledger.

    Parameters
    ----------
    skill_id : str
        A human-readable identifier for the skill (e.g. "python", "solidity").
    score : int
        Numeric score (0–100).
    artifact_path : str, optional
        Path to artifact file to hash.
    """
    _, service = _init_services()

    # Build arguments
    timestamp = int(time.time())

    # Use real file hash if artifact provided, otherwise auto-generate
    if artifact_path:
        artifact_hash = hash_file(artifact_path)
        logger.info("Hashed artifact file: %s", artifact_path)
    else:
        artifact_hash = hash_string(f"{skill_id}:{score}:{timestamp}")

    logger.info("─" * 60)
    logger.info("SUBMIT SKILL RECORD")
    logger.info("─" * 60)
    logger.info("  Skill ID       : %s", skill_id)
    logger.info("  Score           : %d", score)
    logger.info("  Timestamp       : %d", timestamp)
    logger.info("  Artifact hash   : %s", artifact_hash)

    # Submit via contract service
    result = service.submit_skill_record(
        mode="ai-graded",
        domain=skill_id,
        score=score,
        artifact_hash=artifact_hash,
        timestamp=timestamp,
    )

    if result.success:
        logger.info("─" * 60)
        logger.info("✅ SKILL RECORD SUBMITTED SUCCESSFULLY")
        logger.info("─" * 60)
        logger.info("  Transaction ID  : %s", result.transaction_id)
        logger.info("  Confirmed round : %s", result.confirmed_round or "N/A")
        logger.info("  Explorer        : %s", result.explorer_url)
        logger.info("─" * 60)
    else:
        logger.error("❌ Submission failed: %s", result.error)
        sys.exit(1)


def verify_skill_record(skill_id: str) -> None:
    """Verify / read all skill records for the deployer wallet.

    Parameters
    ----------
    skill_id : str
        Filter results to records matching this domain (skill_id).
        Pass "*" to show all records.
    """
    manager, service = _init_services()

    logger.info("─" * 60)
    logger.info("VERIFY SKILL RECORDS")
    logger.info("─" * 60)
    logger.info("  Wallet          : %s", manager.deployer_address)
    logger.info("  Filter (domain) : %s", skill_id if skill_id != "*" else "(all)")

    # Get records via contract service
    result = service.get_skill_records(manager.deployer_address)

    if not result.success:
        logger.error("❌ Failed to retrieve records: %s", result.error)
        sys.exit(1)

    logger.info("  Total records   : %s", result.record_count)

    if not result.records:
        logger.info("─" * 60)
        logger.info("ℹ️  No skill records found for this wallet.")
        logger.info("─" * 60)
        return

    # Filter by domain if requested
    records = result.records
    if skill_id != "*":
        records = [r for r in records if r.get("domain") == skill_id]

    logger.info("─" * 60)
    if not records:
        logger.info("ℹ️  No records found matching domain '%s'.", skill_id)
    else:
        logger.info("📋 SKILL RECORDS (%d found)", len(records))
        logger.info("─" * 60)
        for i, rec in enumerate(records, 1):
            logger.info("")
            logger.info("  Record #%d", i)
            logger.info("    Mode          : %s", rec.get("mode", "?"))
            logger.info("    Domain        : %s", rec.get("domain", "?"))
            logger.info("    Score         : %s", rec.get("score", "?"))
            logger.info("    Artifact Hash : %s", rec.get("artifact_hash", "?"))
            logger.info("    Timestamp     : %s", rec.get("timestamp", "?"))

            if rec.get("decode_error"):
                logger.warning("    ⚠ Decode error: %s", rec["decode_error"])

    logger.info("─" * 60)
    logger.info("✅ Verification complete.")
    logger.info("─" * 60)


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(
        prog="interact",
        description="Verified Protocol — Algorand Testnet Interaction CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # ── submit ───────────────────────────────────────────────────────
    submit_parser = subparsers.add_parser(
        "submit",
        help="Submit a new skill attestation record on-chain",
    )
    submit_parser.add_argument(
        "skill_id",
        type=str,
        help='Skill domain identifier (e.g. "python", "solidity")',
    )
    submit_parser.add_argument(
        "score",
        type=int,
        help="Numeric score (0–100)",
    )
    submit_parser.add_argument(
        "--artifact",
        type=str,
        default=None,
        help="Path to artifact file to hash (optional)",
    )

    # ── verify ───────────────────────────────────────────────────────
    verify_parser = subparsers.add_parser(
        "verify",
        help="Verify / read skill records for the deployer wallet",
    )
    verify_parser.add_argument(
        "skill_id",
        type=str,
        help='Skill domain to filter by, or "*" for all records',
    )

    args = parser.parse_args()

    try:
        if args.command == "submit":
            if not 0 <= args.score <= 100:
                logger.error("Score must be between 0 and 100 (got %d)", args.score)
                sys.exit(1)
            submit_skill_record(args.skill_id, args.score, args.artifact)

        elif args.command == "verify":
            verify_skill_record(args.skill_id)

    except KeyboardInterrupt:
        logger.info("\nInterrupted by user.")
        sys.exit(130)
    except Exception as exc:
        logger.error("Fatal error: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
