import pytest

from forge.mission_runtime.errors import MissionStateError
from forge.mission_runtime.state_machine import assert_transition
from forge.mission_runtime.states import MissionState


def test_valid_transition_is_allowed() -> None:
    assert_transition(
        MissionState.CREATED,
        MissionState.RESOLVING_WORKSPACE,
    )


def test_invalid_transition_is_rejected() -> None:
    with pytest.raises(MissionStateError):
        assert_transition(
            MissionState.CREATED,
            MissionState.COMPLETED,
        )