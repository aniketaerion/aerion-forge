"""Resume controls for paused and recovering runs."""

from __future__ import annotations

from forge.autonomous_execution_v2.errors import ExecutionStateError
from forge.autonomous_execution_v2.models import ExecutionRun
from forge.autonomous_execution_v2.states import ExecutionRunState


def resume_execution_run(run: ExecutionRun) -> ExecutionRun:
    """Resume a paused or recovering execution run."""
    if run.state not in {
        ExecutionRunState.PAUSED,
        ExecutionRunState.RECOVERING,
        ExecutionRunState.AWAITING_APPROVAL,
    }:
        raise ExecutionStateError(
            "Only paused, recovering, or approval-blocked runs can be resumed."
        )

    return run.model_copy(
        update={
            "state": ExecutionRunState.RUNNING,
            "failure_reason": None,
        }
    )