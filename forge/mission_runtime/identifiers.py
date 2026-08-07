"""Deterministic identifiers for the M5.8 Mission Runtime."""

from __future__ import annotations

import hashlib
import json
from enum import Enum
from pathlib import Path
from typing import Any


def _normalize(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, dict):
        return {
            str(key): _normalize(item)
            for key, item in sorted(
                value.items(),
                key=lambda pair: str(pair[0]),
            )
        }
    if isinstance(value, list | tuple | set | frozenset):
        items = [_normalize(item) for item in value]
        if isinstance(value, set | frozenset):
            items = sorted(
                items,
                key=lambda item: json.dumps(
                    item,
                    sort_keys=True,
                    separators=(",", ":"),
                ),
            )
        return items
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    raise TypeError(
        f"Unsupported identifier value: {type(value)!r}"
    )


def deterministic_mission_identifier(
    prefix: str,
    payload: dict[str, Any],
) -> str:
    canonical = json.dumps(
        _normalize(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    digest = hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()[:24]
    return f"{prefix}-{digest}"


def mission_request_identifier(
    payload: dict[str, Any],
) -> str:
    return deterministic_mission_identifier(
        "mission-request",
        payload,
    )


def mission_session_identifier(
    payload: dict[str, Any],
) -> str:
    return deterministic_mission_identifier(
        "mission-session",
        payload,
    )


def mission_checkpoint_identifier(
    payload: dict[str, Any],
) -> str:
    return deterministic_mission_identifier(
        "mission-checkpoint",
        payload,
    )


def mission_approval_identifier(
    payload: dict[str, Any],
) -> str:
    return deterministic_mission_identifier(
        "mission-approval",
        payload,
    )


def mission_evidence_identifier(
    payload: dict[str, Any],
) -> str:
    return deterministic_mission_identifier(
        "mission-evidence",
        payload,
    )


def mission_result_identifier(
    payload: dict[str, Any],
) -> str:
    return deterministic_mission_identifier(
        "mission-result",
        payload,
    )