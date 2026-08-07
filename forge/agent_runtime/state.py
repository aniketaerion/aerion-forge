"""Lifecycle state machine for M3.8 Unified Agent Runtime."""

from __future__ import annotations

from datetime import UTC, datetime

from forge.agent_runtime.errors import AgentRuntimeStateError
from forge.agent_runtime.models import (
    AgentSession,
    AgentSessionStatus,
    AgentStage,
    AgentStageResult,
    AgentStageStatus,
)

_ALLOWED_TRANSITIONS: dict[
    AgentSessionStatus,
    frozenset[AgentSessionStatus],
] = {
    AgentSessionStatus.CREATED: frozenset(
        {
            AgentSessionStatus.PLANNING,
            AgentSessionStatus.AWAITING_APPROVAL,
            AgentSessionStatus.CANCELLED,
        }
    ),
    AgentSessionStatus.PLANNING: frozenset(
        {
            AgentSessionStatus.AWAITING_APPROVAL,
            AgentSessionStatus.EXECUTING,
            AgentSessionStatus.COMPLETED,
            AgentSessionStatus.FAILED,
            AgentSessionStatus.PAUSED,
            AgentSessionStatus.CANCELLED,
        }
    ),
    AgentSessionStatus.AWAITING_APPROVAL: frozenset(
        {
            AgentSessionStatus.PLANNING,
            AgentSessionStatus.EXECUTING,
            AgentSessionStatus.REPAIRING,
            AgentSessionStatus.VERIFYING,
            AgentSessionStatus.PAUSED,
            AgentSessionStatus.CANCELLED,
            AgentSessionStatus.FAILED,
        }
    ),
    AgentSessionStatus.EXECUTING: frozenset(
        {
            AgentSessionStatus.VALIDATING,
            AgentSessionStatus.AWAITING_APPROVAL,
            AgentSessionStatus.FAILED,
            AgentSessionStatus.PAUSED,
            AgentSessionStatus.CANCELLED,
        }
    ),
    AgentSessionStatus.VALIDATING: frozenset(
        {
            AgentSessionStatus.REPAIRING,
            AgentSessionStatus.VERIFYING,
            AgentSessionStatus.COMPLETED,
            AgentSessionStatus.FAILED,
            AgentSessionStatus.PAUSED,
            AgentSessionStatus.CANCELLED,
        }
    ),
    AgentSessionStatus.REPAIRING: frozenset(
        {
            AgentSessionStatus.VALIDATING,
            AgentSessionStatus.AWAITING_APPROVAL,
            AgentSessionStatus.FAILED,
            AgentSessionStatus.PAUSED,
            AgentSessionStatus.CANCELLED,
        }
    ),
    AgentSessionStatus.VERIFYING: frozenset(
        {
            AgentSessionStatus.AWAITING_APPROVAL,
            AgentSessionStatus.COMPLETED,
            AgentSessionStatus.FAILED,
            AgentSessionStatus.PAUSED,
            AgentSessionStatus.CANCELLED,
        }
    ),
    AgentSessionStatus.PAUSED: frozenset(
        {
            AgentSessionStatus.PLANNING,
            AgentSessionStatus.AWAITING_APPROVAL,
            AgentSessionStatus.EXECUTING,
            AgentSessionStatus.VALIDATING,
            AgentSessionStatus.REPAIRING,
            AgentSessionStatus.VERIFYING,
            AgentSessionStatus.CANCELLED,
        }
    ),
    AgentSessionStatus.COMPLETED: frozenset(),
    AgentSessionStatus.FAILED: frozenset(),
    AgentSessionStatus.CANCELLED: frozenset(),
}


def can_transition(
    current: AgentSessionStatus,
    target: AgentSessionStatus,
) -> bool:
    """Return whether the session lifecycle transition is permitted."""
    return target in _ALLOWED_TRANSITIONS[current]


def transition_session(
    session: AgentSession,
    target: AgentSessionStatus,
    *,
    current_stage_id: str | None = None,
) -> AgentSession:
    """Transition a session while preserving immutable history."""
    if target is session.status:
        return session

    if not can_transition(session.status, target):
        raise AgentRuntimeStateError(
            "invalid agent-session transition: "
            f"{session.status.value} -> {target.value}"
        )

    return session.model_copy(
        update={
            "status": target,
            "current_stage_id": current_stage_id,
            "updated_at": datetime.now(UTC),
        }
    )


def completed_stage_ids(
    session: AgentSession,
) -> frozenset[str]:
    """Return successfully completed runtime stage identifiers."""
    return frozenset(
        result.stage_id
        for result in session.stage_results
        if result.status is AgentStageStatus.SUCCEEDED
    )


def failed_required_stage(
    session: AgentSession,
) -> AgentStage | None:
    """Return the first required stage that failed or was blocked."""
    stages = {stage.stage_id: stage for stage in session.stages}

    for result in session.stage_results:
        if result.status not in {
            AgentStageStatus.FAILED,
            AgentStageStatus.BLOCKED,
        }:
            continue

        stage = stages[result.stage_id]
        if stage.required:
            return stage

    return None


def next_ready_stage(
    session: AgentSession,
) -> AgentStage | None:
    """Return the next dependency-satisfied, unexecuted stage."""
    completed = completed_stage_ids(session)
    executed = {
        result.stage_id
        for result in session.stage_results
    }

    for stage in sorted(
        session.stages,
        key=lambda item: item.sequence,
    ):
        if stage.stage_id in executed:
            continue

        if set(stage.depends_on).issubset(completed):
            return stage

    return None


def append_stage_result(
    session: AgentSession,
    result: AgentStageResult,
) -> AgentSession:
    """Append exactly one stage result to immutable session state."""
    known_stage_ids = {
        stage.stage_id for stage in session.stages
    }

    if result.stage_id not in known_stage_ids:
        raise AgentRuntimeStateError(
            f"stage result references unknown stage: {result.stage_id}"
        )

    if any(
        existing.stage_id == result.stage_id
        for existing in session.stage_results
    ):
        raise AgentRuntimeStateError(
            f"stage already has a result: {result.stage_id}"
        )

    return session.model_copy(
        update={
            "stage_results": (
                *session.stage_results,
                result,
            ),
            "current_stage_id": result.stage_id,
            "updated_at": datetime.now(UTC),
        }
    )
