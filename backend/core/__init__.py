"""
Backend Core — Infrastructure Layer
=====================================

Centralized Algorand client management, contract services,
and ARC-4 decoding utilities.
"""

from backend.core.algorand_client import AlgorandClientManager, AlgorandError
from backend.core.arc4_decoder import ARC4Decoder
from backend.core.contract_service import ContractService, SubmissionResult

__all__ = [
    "AlgorandClientManager",
    "AlgorandError",
    "ARC4Decoder",
    "ContractService",
    "SubmissionResult",
]
