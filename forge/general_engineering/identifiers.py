"""Deterministic identifiers for M5.9 general engineering contracts."""

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
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
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
                    ensure_ascii=True,
                ),
            )
        return items
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    raise TypeError(f"Unsupported identifier value: {type(value)!r}")


def deterministic_engineering_identifier(
    prefix: str,
    payload: dict[str, Any],
) -> str:
    canonical = json.dumps(
        _normalize(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]
    return f"{prefix}-{digest}"


def engineering_request_identifier(payload: dict[str, Any]) -> str:
    return deterministic_engineering_identifier("engineering-request", payload)


def repository_evidence_identifier(payload: dict[str, Any]) -> str:
    return deterministic_engineering_identifier("repository-evidence", payload)


def change_requirement_identifier(payload: dict[str, Any]) -> str:
    return deterministic_engineering_identifier("change-requirement", payload)


def change_plan_identifier(payload: dict[str, Any]) -> str:
    return deterministic_engineering_identifier("change-plan", payload)


def edit_operation_identifier(payload: dict[str, Any]) -> str:
    return deterministic_engineering_identifier("edit-operation", payload)


def change_set_identifier(payload: dict[str, Any]) -> str:
    return deterministic_engineering_identifier("change-set", payload)


def validation_plan_identifier(payload: dict[str, Any]) -> str:
    return deterministic_engineering_identifier("validation-plan", payload)


def validation_outcome_identifier(payload: dict[str, Any]) -> str:
    return deterministic_engineering_identifier("validation-outcome", payload)


def repair_proposal_identifier(payload: dict[str, Any]) -> str:
    return deterministic_engineering_identifier("repair-proposal", payload)


def engineering_evidence_identifier(payload: dict[str, Any]) -> str:
    return deterministic_engineering_identifier("engineering-evidence", payload)