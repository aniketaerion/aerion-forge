"""Deterministic identifiers for M3.6 Mission Orchestration."""

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
    """Return a stable identifier from canonical JSON."""
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


def mission_identifier(payload: Mapping[str, Any]) -> str:
    return stable_identifier("mission", payload)


def workflow_identifier(payload: Mapping[str, Any]) -> str:
    return stable_identifier("workflow", payload)


def stage_run_identifier(payload: Mapping[str, Any]) -> str:
    return stable_identifier("stagerun", payload)


def checkpoint_identifier(payload: Mapping[str, Any]) -> str:
    return stable_identifier("checkpoint", payload)


def orchestration_report_identifier(payload: Mapping[str, Any]) -> str:
    return stable_identifier("missionreport", payload)