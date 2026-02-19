"""
Contract Service — VerifiedProtocol Smart Contract Interface
==============================================================

High-level service layer for interacting with the VerifiedProtocol
smart contract on Algorand.

Responsibilities:
    • Load and manage VerifiedProtocolClient
    • Automatic Box MBR calculation and funding
    • Transaction submission with retry logic
    • Record retrieval and decoding
    • Structured result objects
"""

from __future__ import annotations

import logging
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import algokit_utils
from algokit_utils import AlgoAmount, PaymentParams

# Fix import path for smart contract artifacts
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from smart_contracts.artifacts.verified_protocol.verified_protocol_client import (
    GetRecordCountArgs,
    GetSkillRecordsArgs,
    SubmitSkillRecordArgs,
    VerifiedProtocolClient,
)

from backend.core.algorand_client import AlgorandClientManager, get_manager
from backend.core.arc4_decoder import ARC4Decoder

logger = logging.getLogger("backend.core.contract")

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────
APP_ID = 755779875
MBR_FUNDING_AMOUNT = 500_000  # 0.5 ALGO in microAlgos


# ─────────────────────────────────────────────────────────────────────────────
# Result Objects
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class SubmissionResult:
    """Result of skill record submission."""
    success: bool
    transaction_id: str
    confirmed_round: int | None
    explorer_url: str
    error: str | None = None


@dataclass
class RecordQueryResult:
    """Result of record query."""
    wallet: str
    record_count: int
    records: list[dict[str, Any]]
    success: bool
    error: str | None = None


# ─────────────────────────────────────────────────────────────────────────────
# Contract Service
# ─────────────────────────────────────────────────────────────────────────────
class ContractService:
    """Service layer for VerifiedProtocol smart contract operations."""

    def __init__(
        self,
        manager: AlgorandClientManager | None = None,
        app_id: int = APP_ID,
    ) -> None:
        """Initialize contract service.

        Parameters
        ----------
        manager : AlgorandClientManager, optional
            Algorand client manager. If None, uses singleton.
        app_id : int
            Smart contract application ID.
        """
        self.manager = manager or get_manager()
        self.app_id = app_id
        self._client: VerifiedProtocolClient | None = None
        self.decoder = ARC4Decoder()

    @property
    def client(self) -> VerifiedProtocolClient:
        """Get initialized VerifiedProtocolClient."""
        if self._client is None:
            self._client = VerifiedProtocolClient(
                algorand=self.manager.client,
                app_id=self.app_id,
                default_sender=self.manager.deployer_address,
            )
            logger.info(
                "VerifiedProtocolClient initialized — app_id: %d, address: %s",
                self._client.app_id, self._client.app_address
            )
        return self._client

    def submit_skill_record(
        self,
        mode: str,
        domain: str,
        score: int,
        artifact_hash: str,
        timestamp: int | None = None,
    ) -> SubmissionResult:
        """Submit a skill record to the blockchain.

        Parameters
        ----------
        mode : str
            Evidence mode (e.g., "ai-graded", "self-attested").
        domain : str
            Skill domain (e.g., "python", "solidity").
        score : int
            Credibility score (0-100).
        artifact_hash : str
            SHA-256 hash of evidence artifact.
        timestamp : int, optional
            Unix timestamp. If None, uses current time.

        Returns
        -------
        SubmissionResult
            Submission result with transaction details.
        """
        if timestamp is None:
            timestamp = int(time.time())

        try:
            # Step 1: Fund MBR for Box storage (with box existence check)
            start_time = time.time()
            logger.info("Funding Box MBR for skill record submission")
            self._fund_box_mbr(wallet=self.manager.deployer_address)
            funding_duration = time.time() - start_time
            logger.info("[PERF] box_mbr_funding: %.2fs", funding_duration)

            # Step 2: Submit skill record
            args = SubmitSkillRecordArgs(
                mode=mode,
                domain=domain,
                score=score,
                artifact_hash=artifact_hash,
                timestamp=timestamp,
            )

            send_params = self.manager.create_send_params()

            def submit_txn():
                return self.client.send.submit_skill_record(
                    args=args,
                    send_params=send_params,
                )

            result = self.manager.send_and_confirm(
                submit_txn,
                operation_name="submit_skill_record"
            )

            tx_id = result.tx_ids[0] if result.tx_ids else "unknown"
            confirmed_round = getattr(result, "confirmed_round", None)
            explorer_url = f"https://testnet.explorer.perawallet.app/tx/{tx_id}"

            logger.info(
                "✓ Skill record submitted — txid: %s, round: %s",
                tx_id, confirmed_round
            )

            return SubmissionResult(
                success=True,
                transaction_id=tx_id,
                confirmed_round=confirmed_round,
                explorer_url=explorer_url,
            )

        except Exception as exc:
            logger.error("Skill record submission failed: %s", exc, exc_info=True)
            return SubmissionResult(
                success=False,
                transaction_id="",
                confirmed_round=None,
                explorer_url="",
                error=str(exc),
            )

    def submit_skill_record_async(
        self,
        mode: str,
        domain: str,
        score: int,
        artifact_hash: str,
        timestamp: int | None = None,
    ) -> SubmissionResult:
        """Submit a skill record asynchronously (returns immediately).

        Parameters
        ----------
        mode : str
            Evidence mode (e.g., "ai-graded", "self-attested").
        domain : str
            Skill domain (e.g., "python", "solidity").
        score : int
            Credibility score (0-100).
        artifact_hash : str
            SHA-256 hash of evidence artifact.
        timestamp : int, optional
            Unix timestamp. If None, uses current time.

        Returns
        -------
        SubmissionResult
            Submission result with transaction ID (not yet confirmed).
        """
        if timestamp is None:
            timestamp = int(time.time())

        try:
            start_time = time.time()
            
            # Step 1: Fund MBR for Box storage (with box existence check)
            logger.info("Funding Box MBR for skill record submission")
            self._fund_box_mbr(wallet=self.manager.deployer_address)
            funding_duration = time.time() - start_time
            logger.info("[PERF] box_mbr_funding: %.2fs", funding_duration)

            # Step 2: Submit skill record (async - no confirmation wait)
            args = SubmitSkillRecordArgs(
                mode=mode,
                domain=domain,
                score=score,
                artifact_hash=artifact_hash,
                timestamp=timestamp,
            )

            send_params = self.manager.create_send_params()

            def submit_txn():
                return self.client.send.submit_skill_record(
                    args=args,
                    send_params=send_params,
                )

            submit_start = time.time()
            result, tx_id = self.manager.send_transaction(
                submit_txn,
                operation_name="submit_skill_record_async"
            )
            submit_duration = time.time() - submit_start
            logger.info("[PERF] submit_txn: %.2fs", submit_duration)

            explorer_url = f"https://testnet.explorer.perawallet.app/tx/{tx_id}"

            logger.info(
                "✓ Skill record submitted (async) — txid: %s",
                tx_id
            )

            return SubmissionResult(
                success=True,
                transaction_id=tx_id,
                confirmed_round=None,
                explorer_url=explorer_url,
            )

        except Exception as exc:
            logger.error("Skill record submission failed: %s", exc, exc_info=True)
            return SubmissionResult(
                success=False,
                transaction_id="",
                confirmed_round=None,
                explorer_url="",
                error=str(exc),
            )

    def get_skill_records(self, wallet: str) -> RecordQueryResult:
        """Retrieve and decode all skill records for a wallet.

        Parameters
        ----------
        wallet : str
            Algorand wallet address.

        Returns
        -------
        RecordQueryResult
            Query result with decoded records.
        """
        try:
            send_params = self.manager.create_send_params()

            # Step 1: Get record count
            def get_count():
                return self.client.send.get_record_count(
                    args=GetRecordCountArgs(wallet=wallet),
                    send_params=send_params,
                )

            count_result = self.manager.send_and_confirm(
                get_count,
                operation_name="get_record_count"
            )
            record_count = count_result.abi_return or 0

            logger.info("Wallet %s has %d records", wallet[:12] + "...", record_count)

            if record_count == 0:
                return RecordQueryResult(
                    wallet=wallet,
                    record_count=0,
                    records=[],
                    success=True,
                )

            # Step 2: Get raw box data
            def get_records():
                return self.client.send.get_skill_records(
                    args=GetSkillRecordsArgs(wallet=wallet),
                    send_params=send_params,
                )

            raw_result = self.manager.send_and_confirm(
                get_records,
                operation_name="get_skill_records"
            )

            raw_return = raw_result.abi_return
            raw_bytes = bytes(raw_return) if not isinstance(raw_return, bytes) else raw_return

            # Step 3: Decode records
            records = self.decoder.decode_skill_records(raw_bytes)

            # Filter out error records for count validation
            valid_records = [r for r in records if self.decoder.validate_record(r)]

            logger.info(
                "✓ Retrieved %d records (%d valid) for wallet %s",
                len(records), len(valid_records), wallet[:12] + "..."
            )

            return RecordQueryResult(
                wallet=wallet,
                record_count=record_count,
                records=records,
                success=True,
            )

        except Exception as exc:
            logger.error("Failed to retrieve records for %s: %s", wallet, exc, exc_info=True)
            return RecordQueryResult(
                wallet=wallet,
                record_count=0,
                records=[],
                success=False,
                error=str(exc),
            )

    def _check_box_exists(self, wallet: str) -> bool:
        """Check if wallet box already exists.

        Parameters
        ----------
        wallet : str
            Wallet address to check.

        Returns
        -------
        bool
            True if box exists, False otherwise.
        """
        try:
            send_params = self.manager.create_send_params()

            def get_count():
                return self.client.send.get_record_count(
                    args=GetRecordCountArgs(wallet=wallet),
                    send_params=send_params,
                )

            count_result = self.manager.send_and_confirm(
                get_count,
                operation_name="check_box_exists",
                max_retries=1
            )
            return True
        except Exception:
            return False

    def _fund_box_mbr(self, wallet: str | None = None) -> None:
        """Fund Box Minimum Balance Requirement (Idempotent).

        Sends ALGO to the app address to cover Box storage costs.
        If transaction already in ledger, treats as success.

        Parameters
        ----------
        wallet : str, optional
            Wallet address to check if box exists before funding.
        """
        if wallet and self._check_box_exists(wallet):
            logger.debug("✓ Box already exists for wallet, skipping MBR funding")
            return

        try:
            payment_params = PaymentParams(
                amount=AlgoAmount(micro_algo=MBR_FUNDING_AMOUNT),
                sender=self.manager.deployer_address,
                receiver=self.client.app_address,
                validity_window=1000,
            )

            send_params = self.manager.create_send_params()

            def send_payment():
                return self.manager.client.send.payment(
                    payment_params,
                    send_params=send_params,
                )

            self.manager.send_and_confirm(
                send_payment,
                operation_name="fund_box_mbr"
            )

            logger.debug("✓ Box MBR funded: %d microAlgos", MBR_FUNDING_AMOUNT)

        except Exception as exc:
            error_msg = str(exc).lower()
            if "transaction already in ledger" in error_msg or "already in pool" in error_msg:
                logger.debug("✓ Box MBR funding transaction already submitted (idempotent)")
                return
            logger.error("Box MBR funding failed: %s", exc)
            raise


# ─────────────────────────────────────────────────────────────────────────────
# Singleton instance
# ─────────────────────────────────────────────────────────────────────────────
_service: ContractService | None = None


def get_contract_service() -> ContractService:
    """Get singleton ContractService instance.

    Returns
    -------
    ContractService
        Singleton service instance.
    """
    global _service
    if _service is None:
        _service = ContractService()
    return _service
