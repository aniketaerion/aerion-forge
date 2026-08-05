"""Stable identifiers for M3.8 Unified Agent Runtime."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any


def _normalize(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _normalize(item)
            for key, item in sorted(
                value.items(),
                key=lambda pair: str(pair[0]),
            )
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


def agent_request_identifier(payload: Any) -> str:
    """Build a deterministic agent request identifier."""
    return stable_identifier("agent-request", payload)


def agent_session_identifier(payload: Any) -> str:
    """Build a deterministic agent session identifier."""
    return stable_identifier("agent-session", payload)


def agent_stage_identifier(payload: Any) -> str:
    """Build a deterministic agent stage identifier."""
    return stable_identifier("agent-stage", payload)


def agent_event_identifier(payload: Any) -> str:
    """Build a deterministic agent event identifier."""
    return stable_identifier("agent-event", payload)


def agent_checkpoint_identifier(payload: Any) -> str:
    """Build a deterministic agent checkpoint identifier."""
    return stable_identifier("agent-checkpoint", payload)