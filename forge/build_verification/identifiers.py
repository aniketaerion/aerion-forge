"""Stable identifiers for M3.7 Build Verification."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any


def _normalize(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _normalize(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }

    if isinstance(value, Sequence) and not isinstance(
        value,
        str | bytes | bytearray,
    ):
        return [_normalize(item) for item in value]

    if hasattr(value, "model_dump"):
        return _normalize(value.model_dump(mode="json"))

    if hasattr(value, "value"):
        return _normalize(value.value)

    return value


def stable_identifier(prefix: str, payload: Any) -> str:
    """Build a deterministic identifier from normalized JSON."""
    encoded = json.dumps(
        _normalize(payload),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")

    digest = hashlib.sha256(encoded).hexdigest()[:24]
    return f"{prefix}-{digest}"


def verification_request_identifier(payload: Any) -> str:
    return stable_identifier("build-request", payload)


def verification_step_identifier(payload: Any) -> str:
    return stable_identifier("build-step", payload)


def verification_run_identifier(payload: Any) -> str:
    return stable_identifier("build-run", payload)


def verification_evidence_identifier(payload: Any) -> str:
    return stable_identifier("build-evidence", payload)


def release_decision_identifier(payload: Any) -> str:
    return stable_identifier("release-decision", payload)
