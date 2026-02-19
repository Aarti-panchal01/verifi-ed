"""
Verified Protocol — Read & Decode Skill Records
=================================================

Reads on-chain Box data for a given wallet address and decodes
the ARC-4 encoded SkillRecord structs into a JSON array.

Usage:
    poetry run python read_records.py <wallet_address>
    poetry run python read_records.py <wallet_address> --pretty
    poetry run python read_records.py <wallet_address> --output records.json

ARC-4 Decoding Note:
    The contract stores each record as a length-prefixed ARC-4 struct.
    The struct uses dynamic fields (mode, domain, artifact_hash) which
    require offset-based parsing. This script handles all of that
    automatically — no manual decoding step is needed.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from backend.core.algorand_client import get_manager
from backend.core.contract_service import get_contract_service

# ─────────────────────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("read_records")


# ─────────────────────────────────────────────────────────────────────────────
# Main logic
# ─────────────────────────────────────────────────────────────────────────────
def read_records(wallet_address: str) -> list[dict]:
    """Fetch and decode all skill records for a wallet."""
    env_path = Path(__file__).parent / ".env"
    get_manager(env_path)
    service = get_contract_service()

    result = service.get_skill_records(wallet_address)

    if not result.success:
        logger.error("Failed to retrieve records: %s", result.error)
        return []

    logger.info("Record count for %s: %s", wallet_address, result.record_count)

    if not result.records:
        logger.info("No records found for wallet %s", wallet_address)
        return []

    return result.records


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(
        prog="read_records",
        description="Read & decode on-chain skill records for a wallet",
    )
    parser.add_argument(
        "wallet",
        type=str,
        help="Algorand wallet address (58-char base32)",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print the JSON output",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Write JSON output to file instead of stdout",
    )

    args = parser.parse_args()

    try:
        records = read_records(args.wallet)

        indent = 2 if args.pretty else None
        json_str = json.dumps(records, indent=indent, ensure_ascii=False)

        if args.output:
            Path(args.output).write_text(json_str, encoding="utf-8")
            logger.info("Written %d records to %s", len(records), args.output)
        else:
            print(json_str)

    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as exc:
        logger.error("Fatal: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
