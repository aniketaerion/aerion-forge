import pytest

from forge.autonomous_repair.errors import RepairExecutionError
from forge.autonomous_repair.models import RepairExecutionStatus
from forge.autonomous_repair.state import can_transition, transition


def test_valid_state_transition() -> None:
    assert can_transition(
        RepairExecutionStatus.CREATED,
        RepairExecutionStatus.VALIDATED,
    )
    assert transition(
        RepairExecutionStatus.CREATED,
        RepairExecutionStatus.VALIDATED,
    ) is RepairExecutionStatus.VALIDATED


def test_invalid_state_transition_is_rejected() -> None:
    with pytest.raises(RepairExecutionError):
        transition(
            RepairExecutionStatus.CREATED,
            RepairExecutionStatus.SUCCEEDED,
        )


def test_terminal_states_have_no_transitions() -> None:
    assert not can_transition(
        RepairExecutionStatus.SUCCEEDED,
        RepairExecutionStatus.FAILED,
    )