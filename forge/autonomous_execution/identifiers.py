"""Deterministic identifiers for autonomous execution records."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from forge.autonomous_execution.errors import ExecutionIdentifierError
from forge.autonomous_runtime.identifiers import deterministic_identifier


def _identifier(
    prefix: str,
    payload: Mapping[str, Any],
) -> str:
    try:
        return deterministic_identifier(prefix, payload)
    except Exception as exc:  # pragma: no cover - defensive boundary
        raise ExecutionIdentifierError(
            f"Unable to create {prefix} identifier."
        ) from exc


def execution_request_identifier(
    payload: Mapping[str, Any],
) -> str:
    return _identifier("execution-request", payload)


def execution_lease_identifier(
    payload: Mapping[str, Any],
) -> str:
    return _identifier("execution-lease", payload)


def tool_invocation_identifier(
    payload: Mapping[str, Any],
) -> str:
    return _identifier("tool-invocation", payload)


def step_execution_identifier(
    payload: Mapping[str, Any],
) -> str:
    return _identifier("step-execution", payload)


def execution_evidence_identifier(
    payload: Mapping[str, Any],
) -> str:
    return _identifier("execution-evidence", payload)