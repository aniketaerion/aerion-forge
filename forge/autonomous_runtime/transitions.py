"""Authoritative mission-state transition map."""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Final

from forge.autonomous_runtime.errors import MissionStateError
from forge.autonomous_runtime.states import MissionState

_TRANSITIONS: dict[MissionState, frozenset[MissionState]] = {
    MissionState.RECEIVED: frozenset(
        {
            MissionState.QUALIFYING,
            MissionState.CANCELLED,
            MissionState.FAILED,
        }
    ),
    MissionState.QUALIFYING: frozenset(
        {
            MissionState.QUALIFIED,
            MissionState.CLARIFICATION_REQUIRED,
            MissionState.ESCALATED,
            MissionState.FAILED,
            MissionState.CANCELLED,
        }
    ),
    MissionState.CLARIFICATION_REQUIRED: frozenset(
        {
            MissionState.QUALIFYING,
            MissionState.CANCELLED,
            MissionState.FAILED,
        }
    ),
    MissionState.QUALIFIED: frozenset(
        {
            MissionState.CONTEXT_BUILDING,
            MissionState.ESCALATED,
            MissionState.CANCELLED,
            MissionState.FAILED,
        }
    ),
    MissionState.CONTEXT_BUILDING: frozenset(
        {
            MissionState.CONTEXT_READY,
            MissionState.BLOCKED,
            MissionState.ESCALATED,
            MissionState.CANCELLED,
            MissionState.FAILED,
        }
    ),
    MissionState.CONTEXT_READY: frozenset(
        {
            MissionState.PLANNING,
            MissionState.ESCALATED,
            MissionState.CANCELLED,
            MissionState.FAILED,
        }
    ),
    MissionState.PLANNING: frozenset(
        {
            MissionState.PLAN_READY,
            MissionState.BLOCKED,
            MissionState.ESCALATED,
            MissionState.CANCELLED,
            MissionState.FAILED,
        }
    ),
    MissionState.PLAN_READY: frozenset(
        {
            MissionState.AWAITING_APPROVAL,
            MissionState.APPROVED,
            MissionState.ESCALATED,
            MissionState.CANCELLED,
            MissionState.FAILED,
        }
    ),
    MissionState.AWAITING_APPROVAL: frozenset(
        {
            MissionState.APPROVED,
            MissionState.ESCALATED,
            MissionState.CANCELLED,
            MissionState.FAILED,
        }
    ),
    MissionState.APPROVED: frozenset(
        {
            MissionState.EXECUTING,
            MissionState.PAUSED,
            MissionState.CANCELLED,
            MissionState.FAILED,
        }
    ),
    MissionState.EXECUTING: frozenset(
        {
            MissionState.VALIDATING,
            MissionState.PAUSED,
            MissionState.BLOCKED,
            MissionState.ROLLING_BACK,
            MissionState.ESCALATED,
            MissionState.CANCELLED,
            MissionState.FAILED,
        }
    ),
    MissionState.VALIDATING: frozenset(
        {
            MissionState.EXECUTING,
            MissionState.REVIEWING,
            MissionState.PLANNING,
            MissionState.ROLLING_BACK,
            MissionState.ESCALATED,
            MissionState.CANCELLED,
            MissionState.FAILED,
        }
    ),
    MissionState.REVIEWING: frozenset(
        {
            MissionState.COMPLETED,
            MissionState.PLANNING,
            MissionState.ESCALATED,
            MissionState.CANCELLED,
            MissionState.FAILED,
        }
    ),
    MissionState.PAUSED: frozenset(
        {
            MissionState.EXECUTING,
            MissionState.PLANNING,
            MissionState.ESCALATED,
            MissionState.CANCELLED,
            MissionState.FAILED,
        }
    ),
    MissionState.BLOCKED: frozenset(
        {
            MissionState.CONTEXT_BUILDING,
            MissionState.PLANNING,
            MissionState.EXECUTING,
            MissionState.ESCALATED,
            MissionState.CANCELLED,
            MissionState.FAILED,
        }
    ),
    MissionState.ROLLING_BACK: frozenset(
        {
            MissionState.ROLLED_BACK,
            MissionState.ESCALATED,
            MissionState.FAILED,
        }
    ),
    MissionState.ROLLED_BACK: frozenset(
        {
            MissionState.EXECUTING,
            MissionState.PLANNING,
            MissionState.ESCALATED,
            MissionState.CANCELLED,
            MissionState.FAILED,
        }
    ),
    MissionState.ESCALATED: frozenset(
        {
            MissionState.AWAITING_APPROVAL,
            MissionState.PLANNING,
            MissionState.CANCELLED,
            MissionState.FAILED,
        }
    ),
    MissionState.COMPLETED: frozenset(),
    MissionState.FAILED: frozenset(),
    MissionState.CANCELLED: frozenset(),
}

LEGAL_TRANSITIONS: Final[
    Mapping[MissionState, frozenset[MissionState]]
] = MappingProxyType(_TRANSITIONS)


def allowed_targets(
    state: MissionState,
) -> frozenset[MissionState]:
    """Return legal target states for a mission state."""
    return LEGAL_TRANSITIONS[state]


def can_transition(
    current: MissionState,
    target: MissionState,
) -> bool:
    """Return whether a mission transition is legal."""
    return target in allowed_targets(current)


def assert_transition_allowed(
    current: MissionState,
    target: MissionState,
) -> None:
    """Raise when a transition is not permitted."""
    if not can_transition(current, target):
        raise MissionStateError(
            f"Illegal mission transition: {current.value} -> {target.value}"
        )