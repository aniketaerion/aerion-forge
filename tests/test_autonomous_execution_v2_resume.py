import pytest

from forge.autonomous_execution_v2.errors import ExecutionStateError
from forge.autonomous_execution_v2.models import (
    ExecutionRun,
    ExecutionStep,
)
from forge.autonomous_execution_v2.resume import resume_execution_run
from forge.autonomous_execution_v2.states import ExecutionRunState


def run(state: ExecutionRunState) -> ExecutionRun:
    return ExecutionRun(
        run_id="run-1",
        request_id="request-1",
        plan_id="plan-1",
        plan_version=1,
        repository_root="repository",
        repository_fingerprint="fingerprint",
        state=state,
        steps=(
            ExecutionStep(
                step_id="step-1",
                planning_step_id="planning-step-1",
                sequence=1,
                name="Validate",
                description="Validate repository behaviour.",
            ),
        ),
    )


def test_recovering_run_can_resume() -> None:
    resumed = resume_execution_run(run(ExecutionRunState.RECOVERING))

    assert resumed.state is ExecutionRunState.RUNNING


def test_completed_run_cannot_resume() -> None:
    with pytest.raises(ExecutionStateError):
        resume_execution_run(run(ExecutionRunState.SUCCEEDED))