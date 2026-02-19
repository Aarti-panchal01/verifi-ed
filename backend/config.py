"""
Backend — Shared Configuration (DEPRECATED)
=============================================

This module is deprecated. Use backend.core modules instead:
    - backend.core.algorand_client
    - backend.core.contract_service
    - backend.core.arc4_decoder

Kept for backward compatibility only.
"""

from __future__ import annotations

import logging
from pathlib import Path

from backend.core.algorand_client import get_manager
from backend.core.arc4_decoder import ARC4Decoder
from backend.core.contract_service import get_contract_service

logger = logging.getLogger("backend.config")

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────
APP_ID = 755779875


# ─────────────────────────────────────────────────────────────────────────────
# Backward compatibility wrappers
# ─────────────────────────────────────────────────────────────────────────────
def get_clients():
    """DEPRECATED: Use backend.core modules instead."""
    logger.warning("get_clients() is deprecated. Use backend.core modules.")
    manager = get_manager()
    service = get_contract_service()
    return manager.client, service.client, manager.deployer_address


def send_params():
    """DEPRECATED: Use manager.create_send_params() instead."""
    logger.warning("send_params() is deprecated. Use manager.create_send_params().")
    manager = get_manager()
    return manager.create_send_params()


def decode_skill_records(raw: bytes) -> list[dict]:
    """DEPRECATED: Use ARC4Decoder.decode_skill_records() instead."""
    logger.warning("decode_skill_records() is deprecated. Use ARC4Decoder.")
    decoder = ARC4Decoder()
    return decoder.decode_skill_records(raw)


def fetch_records(wallet: str) -> list[dict]:
    """DEPRECATED: Use ContractService.get_skill_records() instead."""
    logger.warning("fetch_records() is deprecated. Use ContractService.")
    service = get_contract_service()
    result = service.get_skill_records(wallet)
    return result.records if result.success else []
