"""
ARC-4 Decoder — Canonical Implementation
==========================================

Single source of truth for decoding ARC-4 encoded SkillRecord structs
from Algorand Box storage.

Wire Format:
    [2 bytes: record_len][record_len bytes: ARC-4 SkillRecord]

ARC-4 SkillRecord Struct Layout:
    Bytes 0-1   : offset to `mode` string
    Bytes 2-3   : offset to `domain` string
    Bytes 4-11  : `score` (uint64, big-endian)
    Bytes 12-13 : offset to `artifact_hash` string
    Bytes 14-21 : `timestamp` (uint64, big-endian)

    Each ARC-4 string: [2-byte length][UTF-8 bytes]
"""

from __future__ import annotations

import logging
import struct
from typing import Any

logger = logging.getLogger("backend.core.arc4")


class ARC4DecodingError(Exception):
    """Raised when ARC-4 decoding fails."""
    pass


class ARC4Decoder:
    """Stateless ARC-4 decoder for SkillRecord structs."""

    @staticmethod
    def decode_skill_records(raw: bytes) -> list[dict[str, Any]]:
        """Decode length-prefixed ARC-4 SkillRecord structs.

        Parameters
        ----------
        raw : bytes
            Raw bytes from Algorand Box storage.

        Returns
        -------
        list[dict]
            List of decoded records with keys:
            - mode: str
            - domain: str
            - score: int
            - artifact_hash: str
            - timestamp: int

        Raises
        ------
        ARC4DecodingError
            If decoding fails critically.
        """
        if not raw:
            return []

        records: list[dict[str, Any]] = []
        offset = 0
        data_len = len(raw)

        while offset < data_len:
            try:
                # Read 2-byte record length prefix
                if offset + 2 > data_len:
                    logger.warning("Incomplete record length at offset %d — stopping", offset)
                    break

                record_len = struct.unpack(">H", raw[offset : offset + 2])[0]
                offset += 2

                if offset + record_len > data_len:
                    logger.warning(
                        "Truncated record at offset %d (expected %d bytes, got %d) — stopping",
                        offset, record_len, data_len - offset
                    )
                    break

                rec_bytes = raw[offset : offset + record_len]
                offset += record_len

                # Decode single record
                record = ARC4Decoder._decode_single_record(rec_bytes)
                records.append(record)

            except Exception as exc:
                logger.error("Failed to decode record at offset %d: %s", offset, exc)
                # Include error record for debugging
                records.append({
                    "decode_error": str(exc),
                    "raw_hex": raw[max(0, offset - 100) : offset + 100].hex(),
                    "offset": offset,
                })
                # Try to continue with next record
                offset += 1

        logger.debug("Decoded %d records from %d bytes", len(records), data_len)
        return records

    @staticmethod
    def _decode_single_record(rec: bytes) -> dict[str, Any]:
        """Decode a single ARC-4 SkillRecord struct.

        Parameters
        ----------
        rec : bytes
            Single record bytes (without length prefix).

        Returns
        -------
        dict
            Decoded record fields.

        Raises
        ------
        ARC4DecodingError
            If record structure is invalid.
        """
        if len(rec) < 22:
            raise ARC4DecodingError(
                f"Record too short: {len(rec)} bytes (minimum 22 required)"
            )

        try:
            # Parse static header (22 bytes)
            mode_offset = struct.unpack(">H", rec[0:2])[0]
            domain_offset = struct.unpack(">H", rec[2:4])[0]
            score = struct.unpack(">Q", rec[4:12])[0]
            artifact_offset = struct.unpack(">H", rec[12:14])[0]
            timestamp = struct.unpack(">Q", rec[14:22])[0]

            # Validate offsets
            if mode_offset >= len(rec):
                raise ARC4DecodingError(f"Invalid mode_offset: {mode_offset}")
            if domain_offset >= len(rec):
                raise ARC4DecodingError(f"Invalid domain_offset: {domain_offset}")
            if artifact_offset >= len(rec):
                raise ARC4DecodingError(f"Invalid artifact_offset: {artifact_offset}")

            # Decode dynamic strings
            mode = ARC4Decoder._read_arc4_string(rec, mode_offset)
            domain = ARC4Decoder._read_arc4_string(rec, domain_offset)
            artifact_hash = ARC4Decoder._read_arc4_string(rec, artifact_offset)

            return {
                "mode": mode,
                "domain": domain,
                "score": score,
                "artifact_hash": artifact_hash,
                "timestamp": timestamp,
            }

        except struct.error as exc:
            raise ARC4DecodingError(f"Struct unpacking failed: {exc}") from exc
        except Exception as exc:
            raise ARC4DecodingError(f"Record decoding failed: {exc}") from exc

    @staticmethod
    def _read_arc4_string(data: bytes, offset: int) -> str:
        """Read ARC-4 encoded string from data at offset.

        Parameters
        ----------
        data : bytes
            Full record bytes.
        offset : int
            Offset to string data.

        Returns
        -------
        str
            Decoded UTF-8 string.

        Raises
        ------
        ARC4DecodingError
            If string cannot be decoded.
        """
        if offset + 2 > len(data):
            raise ARC4DecodingError(
                f"String length prefix out of bounds at offset {offset}"
            )

        try:
            str_len = struct.unpack(">H", data[offset : offset + 2])[0]

            if offset + 2 + str_len > len(data):
                raise ARC4DecodingError(
                    f"String data out of bounds: offset={offset}, len={str_len}, data_len={len(data)}"
                )

            str_bytes = data[offset + 2 : offset + 2 + str_len]
            return str_bytes.decode("utf-8", errors="replace")

        except struct.error as exc:
            raise ARC4DecodingError(f"Failed to read string length: {exc}") from exc
        except UnicodeDecodeError as exc:
            raise ARC4DecodingError(f"UTF-8 decode failed: {exc}") from exc

    @staticmethod
    def validate_record(record: dict[str, Any]) -> bool:
        """Validate decoded record has required fields.

        Parameters
        ----------
        record : dict
            Decoded record.

        Returns
        -------
        bool
            True if record is valid.
        """
        required_fields = {"mode", "domain", "score", "artifact_hash", "timestamp"}
        return required_fields.issubset(record.keys()) and "decode_error" not in record
