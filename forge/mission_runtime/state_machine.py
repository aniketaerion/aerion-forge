"""Mission lifecycle state transitions for M5.8."""

from __future__ import annotations

from forge.mission_runtime.errors import MissionStateError
from forge.mission_runtime.states import MissionState

_ALLOWED: dict[MissionState, frozenset[MissionState]] = {
    MissionState.CREATED: frozenset({
        MissionState.RESOLVING_WORKSPACE,
        MissionState.CANCELLED,
    }),
    MissionState.RESOLVING_WORKSPACE: frozenset({
        MissionState.UNDERSTANDING_REPOSITORY,
        MissionState.FAILED,
        MissionState.CANCELLED,
    }),
    MissionState.UNDERSTANDING_REPOSITORY: frozenset({
        MissionState.SELECTING_CAPABILITIES,
        MissionState.FAILED,
        MissionState.CANCELLED,
    }),
    MissionState.SELECTING_CAPABILITIES: frozenset({
        MissionState.RETRIEVING_CONTEXT,
        MissionState.FAILED,
        MissionState.CANCELLED,
    }),
    MissionState.RETRIEVING_CONTEXT: frozenset({
        MissionState.PLANNING,
        MissionState.FAILED,
        MissionState.CANCELLED,
    }),
    MissionState.PLANNING: frozenset({
        MissionState.VALIDATING_PLAN,
        MissionState.FAILED,
        MissionState.CANCELLED,
    }),
    MissionState.VALIDATING_PLAN: frozenset({
        MissionState.AWAITING_PLAN_APPROVAL,
        MissionState.APPROVED,
        MissionState.FAILED,
        MissionState.CANCELLED,
    }),
    MissionState.AWAITING_PLAN_APPROVAL: frozenset({
        MissionState.APPROVED,
        MissionState.PAUSED,
        MissionState.CANCELLED,
        MissionState.FAILED,
    }),
    MissionState.APPROVED: frozenset({
        MissionState.EXECUTING,
        MissionState.CANCELLED,
    }),
    MissionState.EXECUTING: frozenset({
        MissionState.VERIFYING,
        MissionState.RECOVERING,
        MissionState.PAUSED,
        MissionState.FAILED,
        MissionState.CANCELLED,
    }),
    MissionState.RECOVERING: frozenset({
        MissionState.EXECUTING,
        MissionState.PAUSED,
        MissionState.FAILED,
        MissionState.CANCELLED,
    }),
    MissionState.VERIFYING: frozenset({
        MissionState.DOCUMENTING,
        MissionState.RECOVERING,
        MissionState.FAILED,
        MissionState.CANCELLED,
    }),
    MissionState.DOCUMENTING: frozenset({
        MissionState.GENERATING_REVIEW,
        MissionState.FAILED,
        MissionState.CANCELLED,
    }),
    MissionState.GENERATING_REVIEW: frozenset({
        MissionState.AWAITING_FINAL_APPROVAL,
        MissionState.FAILED,
        MissionState.CANCELLED,
    }),
    MissionState.AWAITING_FINAL_APPROVAL: frozenset({
        MissionState.COMPLETED,
        MissionState.PAUSED,
        MissionState.CANCELLED,
        MissionState.FAILED,
    }),
    MissionState.PAUSED: frozenset({
        MissionState.AWAITING_PLAN_APPROVAL,
        MissionState.EXECUTING,
        MissionState.AWAITING_FINAL_APPROVAL,
        MissionState.CANCELLED,
        MissionState.FAILED,
    }),
    MissionState.COMPLETED: frozenset(),
    MissionState.FAILED: frozenset(),
    MissionState.CANCELLED: frozenset(),
}


def assert_transition(
    current: MissionState,
    target: MissionState,
) -> None:
    if target not in _ALLOWED[current]:
        raise MissionStateError(
            f"Invalid mission state transition: {current.value} -> {target.value}"
        )