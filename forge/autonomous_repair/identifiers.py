"""Deterministic identifiers for M3.5 Autonomous Repair."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any


def sha256_text(value: str) -> str:
    """Return a SHA-256 digest for UTF-8 text."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def stable_identifier(
    prefix: str,
    payload: Mapping[str, Any] | Sequence[Any] | str,
) -> str:
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


def proposal_identifier(payload: Mapping[str, Any]) -> str:
    """Return a stable proposal identifier."""
    return stable_identifier("repairprop", payload)


def execution_request_identifier(payload: Mapping[str, Any]) -> str:
    """Return a stable execution-request identifier."""
    return stable_identifier("repairexec", payload)


def execution_session_identifier(payload: Mapping[str, Any]) -> str:
    """Return a stable execution-session identifier."""
    return stable_identifier("repairsess", payload)


def patch_identifier(payload: Mapping[str, Any]) -> str:
    """Return a stable repair-patch identifier."""
    return stable_identifier("repairpatch", payload)