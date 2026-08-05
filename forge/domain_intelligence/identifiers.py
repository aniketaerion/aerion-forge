"""Deterministic identifiers for domain intelligence."""

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

    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return [_normalize(item) for item in value]

    if hasattr(value, "model_dump"):
        return _normalize(value.model_dump(mode="json"))

    if hasattr(value, "value"):
        return _normalize(value.value)

    return value


def stable_identifier(prefix: str, payload: Any) -> str:
    encoded = json.dumps(
        _normalize(payload),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")

    digest = hashlib.sha256(encoded).hexdigest()[:24]
    return f"{prefix}-{digest}"


def domain_plugin_identifier(payload: Any) -> str:
    return stable_identifier("domain-plugin", payload)


def frontend_project_identifier(payload: Any) -> str:
    return stable_identifier("frontend-project", payload)


def frontend_finding_identifier(payload: Any) -> str:
    return stable_identifier("frontend-finding", payload)


def frontend_report_identifier(payload: Any) -> str:
    return stable_identifier("frontend-report", payload)