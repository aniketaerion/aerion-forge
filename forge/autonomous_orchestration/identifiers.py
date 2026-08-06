"""Deterministic identifiers for orchestration records."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from forge.autonomous_orchestration.errors import (
    OrchestrationIdentifierError,
)
from forge.autonomous_runtime.identifiers import deterministic_identifier


def _identifier(
    prefix: str,
    payload: Mapping[str, Any],
) -> str:
    try:
        return deterministic_identifier(prefix, payload)
    except Exception as exc:  # pragma: no cover - defensive boundary
        raise OrchestrationIdentifierError(
            f"Unable to create {prefix} identifier."
        ) from exc


def orchestration_request_identifier(
    payload: Mapping[str, Any],
) -> str:
    return _identifier("orchestration-request", payload)


def mission_session_identifier(
    payload: Mapping[str, Any],
) -> str:
    return _identifier("mission-session", payload)


def orchestration_iteration_identifier(
    payload: Mapping[str, Any],
) -> str:
    return _identifier("orchestration-iteration", payload)


def session_checkpoint_identifier(
    payload: Mapping[str, Any],
) -> str:
    return _identifier("session-checkpoint", payload)


def orchestration_stop_identifier(
    payload: Mapping[str, Any],
) -> str:
    return _identifier("orchestration-stop", payload)