import pytest

from forge.autonomous_orchestration.errors import (
    OrchestrationStateError,
)
from forge.autonomous_orchestration.states import OrchestrationState
from forge.autonomous_orchestration.transitions import (
    assert_orchestration_transition,
)


def test_legal_transition_passes() -> None:
    assert_orchestration_transition(
        OrchestrationState.CREATED,
        OrchestrationState.INITIALIZING,
    )


def test_illegal_transition_is_rejected() -> None:
    with pytest.raises(OrchestrationStateError):
        assert_orchestration_transition(
            OrchestrationState.CREATED,
            OrchestrationState.STEP_EXECUTING,
        )


def test_terminal_session_cannot_resume() -> None:
    with pytest.raises(OrchestrationStateError):
        assert_orchestration_transition(
            OrchestrationState.COMPLETED,
            OrchestrationState.RESUME_VALIDATING,
        )