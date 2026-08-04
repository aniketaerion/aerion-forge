"""Deterministic identifiers and fingerprints for safe code editing."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any


def sha256_text(value: str) -> str:
    """Return the SHA-256 digest for UTF-8 text."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def source_fingerprint(content: str) -> str:
    """Return a deterministic source-content fingerprint."""
    return sha256_text(content)


def stable_identifier(prefix: str, payload: Mapping[str, Any] | Sequence[Any] | str) -> str:
    """Build a stable identifier from canonical JSON."""
    if isinstance(payload, str):
        canonical = payload
    else:
        canonical = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            default=str,
        )
    return f"{prefix}_{sha256_text(canonical)[:24]}"


def operation_identifier(payload: Mapping[str, Any]) -> str:
    """Return a stable operation identifier."""
    return stable_identifier("editop", payload)


def request_identifier(payload: Mapping[str, Any]) -> str:
    """Return a stable request identifier."""
    return stable_identifier("editreq", payload)


def transaction_identifier(payload: Mapping[str, Any]) -> str:
    """Return a stable transaction identifier."""
    return stable_identifier("edittxn", payload)