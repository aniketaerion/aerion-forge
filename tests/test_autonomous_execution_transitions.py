import pytest

from forge.autonomous_execution.errors import ExecutionContractError
from forge.autonomous_execution.execution_transitions import (
    assert_execution_transition,
)
from forge.autonomous_execution.states import StepExecutionState


def test_legal_execution_transition_passes() -> None:
    assert_execution_transition(
        StepExecutionState.PENDING,
        StepExecutionState.ELIGIBILITY_CHECK,
    )


def test_illegal_execution_transition_is_rejected() -> None:
    with pytest.raises(ExecutionContractError):
        assert_execution_transition(
            StepExecutionState.PENDING,
            StepExecutionState.TOOL_RUNNING,
        )


def test_terminal_execution_cannot_resume() -> None:
    with pytest.raises(ExecutionContractError):
        assert_execution_transition(
            StepExecutionState.SUCCEEDED,
            StepExecutionState.READY,
        )