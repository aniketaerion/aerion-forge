"""Deterministic identifiers for autonomous-runtime records."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from forge.autonomous_runtime.errors import MissionIdentifierError


def _normalize(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return value.as_posix()
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
    if isinstance(value, str | int | float | bool) or value is None:
        return value

    raise MissionIdentifierError(
        f"Unsupported identifier value: {type(value).__name__}"
    )


def deterministic_identifier(
    prefix: str,
    payload: Mapping[str, Any],
) -> str:
    """Create a stable identifier from a JSON-compatible payload."""
    normalized_prefix = prefix.strip().lower().replace("_", "-")

    if not normalized_prefix:
        raise MissionIdentifierError(
            "Identifier prefix must not be empty."
        )

    encoded = json.dumps(
        _normalize(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    digest = hashlib.sha256(encoded).hexdigest()[:24]

    return f"{normalized_prefix}-{digest}"


def mission_request_identifier(payload: Mapping[str, Any]) -> str:
    return deterministic_identifier("mission-request", payload)


def mission_identifier(payload: Mapping[str, Any]) -> str:
    return deterministic_identifier("mission", payload)


def mission_context_identifier(payload: Mapping[str, Any]) -> str:
    return deterministic_identifier("mission-context", payload)


def mission_plan_identifier(payload: Mapping[str, Any]) -> str:
    return deterministic_identifier("mission-plan", payload)


def mission_step_identifier(payload: Mapping[str, Any]) -> str:
    return deterministic_identifier("mission-step", payload)


def mission_event_identifier(payload: Mapping[str, Any]) -> str:
    return deterministic_identifier("mission-event", payload)


def mission_checkpoint_identifier(payload: Mapping[str, Any]) -> str:
    return deterministic_identifier("mission-checkpoint", payload)


def validation_evidence_identifier(payload: Mapping[str, Any]) -> str:
    return deterministic_identifier("validation-evidence", payload)


def mission_outcome_identifier(payload: Mapping[str, Any]) -> str:
    return deterministic_identifier("mission-outcome", payload)