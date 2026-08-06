import pytest

from forge.autonomous_runtime.errors import MissionStateError
from forge.autonomous_runtime.states import MissionState
from forge.autonomous_runtime.transitions import (
    allowed_targets,
    assert_transition_allowed,
    can_transition,
)


def test_primary_transition_is_allowed() -> None:
    assert can_transition(
        MissionState.RECEIVED,
        MissionState.QUALIFYING,
    )


def test_terminal_states_have_no_targets() -> None:
    assert allowed_targets(MissionState.COMPLETED) == frozenset()
    assert allowed_targets(MissionState.FAILED) == frozenset()
    assert allowed_targets(MissionState.CANCELLED) == frozenset()


def test_illegal_transition_is_rejected() -> None:
    with pytest.raises(MissionStateError):
        assert_transition_allowed(
            MissionState.RECEIVED,
            MissionState.EXECUTING,
        )