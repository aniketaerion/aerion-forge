"""Stable deterministic identifiers for autonomous memory."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from forge.autonomous_memory.errors import MemoryIdentifierError


def _normalize(value: Any) -> Any:
    if isinstance(value, Mapping):
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
    return value


def deterministic_memory_identifier(
    prefix: str,
    payload: Mapping[str, Any],
) -> str:
    if not prefix.strip():
        raise MemoryIdentifierError(
            "Identifier prefix cannot be empty."
        )

    try:
        canonical = json.dumps(
            _normalize(payload),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
    except (TypeError, ValueError) as exc:
        raise MemoryIdentifierError(
            f"Unable to serialize payload for {prefix}."
        ) from exc

    digest = hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()[:24]

    return f"{prefix}-{digest}"


def memory_observation_identifier(
    payload: Mapping[str, Any],
) -> str:
    return deterministic_memory_identifier(
        "memory-observation",
        payload,
    )


def memory_record_identifier(
    payload: Mapping[str, Any],
) -> str:
    return deterministic_memory_identifier(
        "memory-record",
        payload,
    )


def memory_provenance_identifier(
    payload: Mapping[str, Any],
) -> str:
    return deterministic_memory_identifier(
        "memory-provenance",
        payload,
    )


def memory_query_identifier(
    payload: Mapping[str, Any],
) -> str:
    return deterministic_memory_identifier(
        "memory-query",
        payload,
    )


def learning_record_identifier(
    payload: Mapping[str, Any],
) -> str:
    return deterministic_memory_identifier(
        "learning-record",
        payload,
    )