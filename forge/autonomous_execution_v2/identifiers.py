"""Deterministic identifiers for M5.7 execution."""

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


def deterministic_identifier(
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


def execution_request_identifier(
    payload: dict[str, Any],
) -> str:
    return deterministic_identifier("execution-request-v2", payload)


def execution_run_identifier(
    payload: dict[str, Any],
) -> str:
    return deterministic_identifier("execution-run-v2", payload)


def execution_step_identifier(
    payload: dict[str, Any],
) -> str:
    return deterministic_identifier("execution-step-v2", payload)


def execution_attempt_identifier(
    payload: dict[str, Any],
) -> str:
    return deterministic_identifier("execution-attempt-v2", payload)


def execution_evidence_identifier(
    payload: dict[str, Any],
) -> str:
    return deterministic_identifier("execution-evidence-v2", payload)