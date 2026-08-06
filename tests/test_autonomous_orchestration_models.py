import pytest
from pydantic import ValidationError

from forge.autonomous_orchestration.models import (
    MissionSession,
    OrchestrationIteration,
    OrchestrationStop,
    session_is_resumable,
)
from forge.autonomous_orchestration.states import (
    IterationOutcome,
    OrchestrationState,
    OrchestrationStopKind,
)


def session(
    *,
    state: OrchestrationState = OrchestrationState.CREATED,
    stop_reason: str | None = None,
) -> MissionSession:
    return MissionSession(
        session_id="session-1",
        mission_id="mission-1",
        plan_id="plan-1",
        plan_version=1,
        repository_root="repository",
        state=state,
        stop_reason=stop_reason,
    )


def test_terminal_session_requires_stop_reason() -> None:
    with pytest.raises(ValidationError):
        session(state=OrchestrationState.COMPLETED)


def test_completed_step_cannot_be_current_step() -> None:
    with pytest.raises(ValidationError):
        MissionSession(
            session_id="session-1",
            mission_id="mission-1",
            plan_id="plan-1",
            plan_version=1,
            repository_root="repository",
            current_step_id="step-1",
            completed_step_ids=("step-1",),
        )


def test_execution_outcome_requires_execution_id() -> None:
    with pytest.raises(ValidationError):
        OrchestrationIteration(
            iteration_id="iteration-1",
            session_id="session-1",
            sequence=1,
            mission_version_before=1,
            outcome=IterationOutcome.STEP_SUCCEEDED,
        )


def test_terminal_stop_cannot_be_resumable() -> None:
    with pytest.raises(ValidationError):
        OrchestrationStop(
            stop_id="stop-1",
            session_id="session-1",
            stop_kind=OrchestrationStopKind.COMPLETED,
            reason="Mission completed.",
            resumable=True,
        )


def test_paused_session_is_resumable() -> None:
    assert session_is_resumable(
        session(state=OrchestrationState.PAUSED)
    )