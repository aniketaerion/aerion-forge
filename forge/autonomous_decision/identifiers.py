"""Stable deterministic identifiers for decision records."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from forge.autonomous_decision.errors import DecisionIdentifierError


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
        normalized = [_normalize(item) for item in value]
        if isinstance(value, set | frozenset):
            normalized = sorted(
                normalized,
                key=lambda item: json.dumps(
                    item,
                    sort_keys=True,
                    separators=(",", ":"),
                ),
            )
        return normalized

    return value


def deterministic_decision_identifier(
    prefix: str,
    payload: Mapping[str, Any],
) -> str:
    """Return a stable identifier from canonical JSON."""
    if not prefix.strip():
        raise DecisionIdentifierError(
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
        raise DecisionIdentifierError(
            f"Unable to serialize identifier payload for {prefix}."
        ) from exc

    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]
    return f"{prefix}-{digest}"


def decision_request_identifier(
    payload: Mapping[str, Any],
) -> str:
    return deterministic_decision_identifier(
        "decision-request",
        payload,
    )


def decision_context_identifier(
    payload: Mapping[str, Any],
) -> str:
    return deterministic_decision_identifier(
        "decision-context",
        payload,
    )


def candidate_action_identifier(
    payload: Mapping[str, Any],
) -> str:
    return deterministic_decision_identifier(
        "candidate-action",
        payload,
    )


def candidate_assessment_identifier(
    payload: Mapping[str, Any],
) -> str:
    return deterministic_decision_identifier(
        "candidate-assessment",
        payload,
    )


def decision_record_identifier(
    payload: Mapping[str, Any],
) -> str:
    return deterministic_decision_identifier(
        "decision-record",
        payload,
    )


def decision_stop_identifier(
    payload: Mapping[str, Any],
) -> str:
    return deterministic_decision_identifier(
        "decision-stop",
        payload,
    )