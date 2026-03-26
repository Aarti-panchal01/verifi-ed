"""
Algorand Client Manager — Production Infrastructure
=====================================================

Centralized Algorand client initialization with:
    • Exponential backoff retry logic
    • Structured exception handling
    • Transaction confirmation waiting
    • Connection pooling
    • Timeout management
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Callable

import algokit_utils
from algokit_utils.models.transaction import SendParams
from dotenv import load_dotenv

logger = logging.getLogger("backend.core.algorand")

# region agent log
import json

_AGENT_DEBUG_LOG_PATH = Path(r"c:\Users\Aarti Panchal\Downloads\verifi.ed-main\verifi.ed\.cursor\debug.log")


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

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────
MAX_RETRIES = 3
BASE_RETRY_DELAY = 2.0
MAX_RETRY_DELAY = 16.0
DEFAULT_VALIDITY_WINDOW = 1000
DEFAULT_TIMEOUT = 30.0

# Public TestNet Defaults (AlgoNode)
TESTNET_ALGOD_SERVER = "https://testnet-api.algonode.cloud"
TESTNET_ALGOD_PORT = 443
TESTNET_ALGOD_TOKEN = ""
TESTNET_INDEXER_SERVER = "https://testnet-idx.algonode.cloud"
TESTNET_INDEXER_PORT = 443
TESTNET_INDEXER_TOKEN = ""


# ─────────────────────────────────────────────────────────────────────────────
# Exceptions
# ─────────────────────────────────────────────────────────────────────────────
class AlgorandError(Exception):
    """Base exception for Algorand operations."""
    pass


class TransactionError(AlgorandError):
    """Transaction submission or confirmation failed."""
    pass


class RateLimitError(AlgorandError):
    """API rate limit exceeded."""
    pass


class NetworkError(AlgorandError):
    """Network connectivity issue."""
    pass


# ─────────────────────────────────────────────────────────────────────────────
# Client Manager
# ─────────────────────────────────────────────────────────────────────────────
class AlgorandClientManager:
    """Manages Algorand client lifecycle and provides retry logic."""

    def __init__(self, env_path: Path | None = None) -> None:
        """Initialize Algorand client manager.

        Parameters
        ----------
        env_path : Path, optional
            Path to .env file. If None, searches parent directories.
        """
        if env_path:
            load_dotenv(env_path)
        else:
            load_dotenv()

        self._client: algokit_utils.AlgorandClient | None = None
        self._deployer_address: str | None = None
        self._initialized = False

    def initialize(self) -> None:
        """Initialize Algorand client and deployer account."""
        if self._initialized:
            return

        import os
        # region agent log
        _agent_log(
            hypothesisId="H-deployer-missing",
            runId="pre-fix",
            location="backend/core/algorand_client.py:initialize",
            message="Initializing Algorand client; env presence (no values).",
            data={
                "has_ALGOD_SERVER": bool(os.getenv("ALGOD_SERVER")),
                "has_INDEXER_SERVER": bool(os.getenv("INDEXER_SERVER")),
                "has_DEPLOYER_MNEMONIC": bool(os.getenv("DEPLOYER_MNEMONIC")),
                "has_DEPLOYER": bool(os.getenv("DEPLOYER")),
            },
        )
        # endregion agent log
        # Default to TestNet if no server configured (prevents [WinError 10061])
        if not os.getenv("ALGOD_SERVER"):
            logger.info("No ALGOD_SERVER found in environment. Defaulting to AlgoNode TestNet.")
            os.environ["ALGOD_SERVER"] = TESTNET_ALGOD_SERVER
            os.environ["ALGOD_PORT"] = str(TESTNET_ALGOD_PORT)
            os.environ["ALGOD_TOKEN"] = TESTNET_ALGOD_TOKEN
            
        if not os.getenv("INDEXER_SERVER"):
            os.environ["INDEXER_SERVER"] = TESTNET_INDEXER_SERVER
            os.environ["INDEXER_PORT"] = str(TESTNET_INDEXER_PORT)
            os.environ["INDEXER_TOKEN"] = TESTNET_INDEXER_TOKEN

        try:
            self._client = algokit_utils.AlgorandClient.from_environment()
            self._client.set_default_validity_window(DEFAULT_VALIDITY_WINDOW)

            # Some endpoints might fail if no DEPLOYER mnemonic available
            # but for view-only (reputation) we don't necessarily need it.
            try:
                deployer = self._client.account.from_environment("DEPLOYER")
                self._deployer_address = deployer.address
            except Exception as e:
                logger.warning("No DEPLOYER account in environment. On-chain submission might fail: %s", e)
                # Use a dummy if absent for client properties to exist
                self._deployer_address = "A" * 58 

            # region agent log
            _agent_log(
                hypothesisId="H-deployer-missing",
                runId="pre-fix",
                location="backend/core/algorand_client.py:initialize",
                message="Algorand client initialized; deployer address shape.",
                data={
                    "deployer_address_prefix": (self._deployer_address or "")[:6],
                    "deployer_address_len": len(self._deployer_address or ""),
                    "deployer_is_dummy_all_A": bool(self._deployer_address) and set(self._deployer_address) == {"A"},
                },
            )
            # endregion agent log

            self._initialized = True
            logger.info("Algorand client initialized — deployer: %s", self._deployer_address)

        except Exception as exc:
            logger.error("Failed to initialize Algorand client: %s", exc)
            raise AlgorandError(f"Client initialization failed: {exc}") from exc

    @property
    def client(self) -> algokit_utils.AlgorandClient:
        """Get initialized Algorand client."""
        if not self._initialized:
            self.initialize()
        return self._client  # type: ignore[return-value]

    @property
    def deployer_address(self) -> str:
        """Get deployer wallet address."""
        if not self._initialized:
            self.initialize()
        return self._deployer_address  # type: ignore[return-value]

    def send_and_confirm(
        self,
        txn_callable: Callable[[], Any],
        operation_name: str = "transaction",
        max_retries: int = MAX_RETRIES,
    ) -> Any:
        """Send transaction with exponential backoff retry logic.

        Parameters
        ----------
        txn_callable : Callable
            Function that executes the transaction.
        operation_name : str
            Human-readable operation name for logging.
        max_retries : int
            Maximum retry attempts.

        Returns
        -------
        Any
            Transaction result from txn_callable.

        Raises
        ------
        TransactionError
            If transaction fails after all retries.
        RateLimitError
            If rate limit is exceeded.
        NetworkError
            If network connectivity fails.
        """
        last_exception: Exception | None = None
        delay = BASE_RETRY_DELAY

        for attempt in range(1, max_retries + 1):
            try:
                logger.debug(
                    "Executing %s (attempt %d/%d)",
                    operation_name, attempt, max_retries
                )
                result = txn_callable()
                logger.info("✓ %s completed successfully", operation_name)
                return result

            except Exception as exc:
                last_exception = exc
                error_msg = str(exc).lower()

                # Classify error
                if "rate limit" in error_msg or "429" in error_msg:
                    if attempt >= max_retries:
                        raise RateLimitError(f"Rate limit exceeded: {exc}") from exc
                    logger.warning(
                        "Rate limit hit on %s (attempt %d/%d) — retrying in %.1fs",
                        operation_name, attempt, max_retries, delay
                    )

                elif self._is_retriable(exc):
                    if attempt >= max_retries:
                        raise TransactionError(
                            f"{operation_name} failed after {max_retries} attempts: {exc}"
                        ) from exc
                    logger.warning(
                        "Retriable error on %s (attempt %d/%d) — retrying in %.1fs: %s",
                        operation_name, attempt, max_retries, delay, exc
                    )

                elif "connection" in error_msg or "timeout" in error_msg:
                    if attempt >= max_retries:
                        raise NetworkError(f"Network error: {exc}") from exc
                    logger.warning(
                        "Network error on %s (attempt %d/%d) — retrying in %.1fs",
                        operation_name, attempt, max_retries, delay
                    )

                else:
                    # Non-retriable error
                    logger.error("Non-retriable error on %s: %s", operation_name, exc)
                    raise TransactionError(f"{operation_name} failed: {exc}") from exc

                # Exponential backoff
                time.sleep(delay)
                delay = min(delay * 2, MAX_RETRY_DELAY)

        # Should not reach here, but handle gracefully
        raise TransactionError(
            f"{operation_name} failed after {max_retries} attempts: {last_exception}"
        ) from last_exception
    def send_transaction(
        self,
        txn_callable: Callable[[], Any],
        operation_name: str = "transaction",
        max_retries: int = MAX_RETRIES,
    ) -> tuple[Any, str]:
        """Send transaction without waiting for confirmation.

        Parameters
        ----------
        txn_callable : Callable
            Function that executes the transaction.
        operation_name : str
            Human-readable operation name for logging.
        max_retries : int
            Maximum retry attempts.

        Returns
        -------
        tuple[Any, str]
            (Transaction result, transaction ID)

        Raises
        ------
        TransactionError
            If transaction submission fails after all retries.
        """
        last_exception: Exception | None = None
        delay = BASE_RETRY_DELAY

        for attempt in range(1, max_retries + 1):
            try:
                logger.debug(
                    "Sending %s (attempt %d/%d)",
                    operation_name, attempt, max_retries
                )
                result = txn_callable()
                tx_id = result.tx_ids[0] if hasattr(result, 'tx_ids') and result.tx_ids else "unknown"
                logger.info("✓ %s sent successfully — txid: %s", operation_name, tx_id)
                return result, tx_id

            except Exception as exc:
                last_exception = exc
                error_msg = str(exc).lower()

                if self._is_retriable(exc) and attempt < max_retries:
                    logger.warning(
                        "Retriable error on %s (attempt %d/%d) — retrying in %.1fs: %s",
                        operation_name, attempt, max_retries, delay, exc
                    )
                    time.sleep(delay)
                    delay = min(delay * 2, MAX_RETRY_DELAY)
                else:
                    logger.error("Transaction send failed on %s: %s", operation_name, exc)
                    raise TransactionError(f"{operation_name} send failed: {exc}") from exc

        raise TransactionError(
            f"{operation_name} failed after {max_retries} attempts: {last_exception}"
        ) from last_exception


    def wait_for_confirmation(
        self,
        txid: str,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> dict[str, Any]:
        """Wait for transaction confirmation.

        Parameters
        ----------
        txid : str
            Transaction ID to wait for.
        timeout : float
            Maximum wait time in seconds.

        Returns
        -------
        dict
            Confirmed transaction info.

        Raises
        ------
        TransactionError
            If confirmation times out or fails.
        """
        try:
            logger.debug("Waiting for confirmation of txid: %s", txid)
            start = time.time()

            # Use AlgoKit's built-in confirmation waiting
            result = self.client.client.algod.pending_transaction_info(txid)

            while time.time() - start < timeout:
                if result.get("confirmed-round"):
                    logger.info(
                        "✓ Transaction %s confirmed in round %d",
                        txid, result["confirmed-round"]
                    )
                    return result

                time.sleep(1)
                result = self.client.client.algod.pending_transaction_info(txid)

            raise TransactionError(f"Transaction {txid} confirmation timeout after {timeout}s")

        except Exception as exc:
            logger.error("Failed to confirm transaction %s: %s", txid, exc)
            raise TransactionError(f"Confirmation failed: {exc}") from exc

    def create_send_params(
        self,
        max_rounds_to_wait: int = DEFAULT_VALIDITY_WINDOW,
        populate_resources: bool = True,
    ) -> SendParams:
        """Create SendParams with standard configuration.

        Parameters
        ----------
        max_rounds_to_wait : int
            Maximum rounds to wait for confirmation.
        populate_resources : bool
            Whether to auto-populate app call resources.

        Returns
        -------
        SendParams
            Configured send parameters.
        """
        return SendParams(
            max_rounds_to_wait=max_rounds_to_wait,
            populate_app_call_resources=populate_resources,
        )

    @staticmethod
    def _is_retriable(exc: Exception) -> bool:
        """Check if exception is retriable.

        Parameters
        ----------
        exc : Exception
            Exception to check.

        Returns
        -------
        bool
            True if error is transient and retriable.
        """
        msg = str(exc).lower()
        retriable_patterns = [
            "txn dead",
            "round outside",
            "transaction expired",
            "stale",
            "pool error",
        ]
        return any(pattern in msg for pattern in retriable_patterns)


# ─────────────────────────────────────────────────────────────────────────────
# Singleton instance
# ─────────────────────────────────────────────────────────────────────────────
_manager: AlgorandClientManager | None = None


def get_manager(env_path: Path | None = None) -> AlgorandClientManager:
    """Get singleton AlgorandClientManager instance.

    Parameters
    ----------
    env_path : Path, optional
        Path to .env file for first initialization.

    Returns
    -------
    AlgorandClientManager
        Singleton manager instance.
    """
    global _manager
    if _manager is None:
        _manager = AlgorandClientManager(env_path)
        _manager.initialize()
    return _manager
