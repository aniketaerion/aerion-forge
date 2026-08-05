"""Recovery helpers for M3.8 Unified Agent Runtime."""

from __future__ import annotations

from forge.agent_runtime.errors import AgentRuntimeRecoveryError
from forge.agent_runtime.models import (
    AgentCheckpoint,
    AgentSession,
    AgentSessionStatus,
)


def recover_session(
    session: AgentSession,
    checkpoint: AgentCheckpoint,
) -> AgentSession:
    if session.session_id != checkpoint.session_id:
        raise AgentRuntimeRecoveryError(
            "checkpoint does not belong to the supplied session"
        )

    if checkpoint.status in {
        AgentSessionStatus.COMPLETED,
        AgentSessionStatus.FAILED,
        AgentSessionStatus.CANCELLED,
    }:
        raise AgentRuntimeRecoveryError(
            "terminal checkpoint cannot be resumed"
        )

    completed = set(checkpoint.completed_stage_ids)
    results = tuple(
        result
        for result in session.stage_results
        if result.stage_id in completed
    )

    return session.model_copy(
        update={
            "status": checkpoint.status,
            "current_stage_id": checkpoint.current_stage_id,
            "stage_results": results,
        }
    )