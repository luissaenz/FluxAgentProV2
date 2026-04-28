"""src/services/integrity.py — Integrity verification using SHA256.

Focuses on in-memory streams to avoid disk I/O and Path Traversal.
"""

from __future__ import annotations

import hashlib
import io
import logging

logger = logging.getLogger(__name__)


def calculate_sha256(data: bytes | io.BytesIO) -> str:
    """Calculate the SHA256 hash of the given data.

    Returns the hash prefixed with 'sha256:'.
    """
    sha256_hash = hashlib.sha256()

    if isinstance(data, io.BytesIO):
        # Reset pointer just in case
        data.seek(0)
        # Read in chunks to be memory efficient even if in RAM
        for chunk in iter(lambda: data.read(4096), b""):
            sha256_hash.update(chunk)
        data.seek(0)  # Reset for next reader
    else:
        sha256_hash.update(data)

    return f"sha256:{sha256_hash.hexdigest()}"


def verify_integrity(data: bytes, expected_hash: str) -> bool:
    """Verify that the data matches the expected hash."""
    actual_hash = calculate_sha256(data)
    if actual_hash != expected_hash:
        logger.warning(
            "Integrity check failed. Expected: %s, Actual: %s",
            expected_hash, actual_hash
        )
        return False
    return True
