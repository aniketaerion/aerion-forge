import pytest

from forge.autonomous_runtime.errors import MissionStateError
from forge.autonomous_runtime.lifecycle import transition_mission
from forge.autonomous_runtime.models import (
    AutonomousMission,
    MissionRequest,
)
from forge.autonomous_runtime.states import (
    AuthorityLevel,
    MissionState,
)


def mission(
    state: MissionState = MissionState.RECEIVED,
) -> AutonomousMission:
    return AutonomousMission(
        mission_id="mission-1",
        request=MissionRequest(
            request_id="request-1",
            objective="Control mission lifecycle.",
            repository_root="repository",
            requested_authority=AuthorityLevel.A2_MODIFY,
            requested_by="Aerion",
        ),
        state=state,
        granted_authority=AuthorityLevel.A2_MODIFY,
    )


def test_transition_returns_new_versioned_snapshot() -> None:
    original = mission()
    updated = transition_mission(
        original,
        MissionState.QUALIFYING,
    )

    assert original.state is MissionState.RECEIVED
    assert updated.state is MissionState.QUALIFYING
    assert updated.version == original.version + 1


def test_terminal_transition_requires_outcome() -> None:
    with pytest.raises(MissionStateError):
        transition_mission(
            mission(MissionState.REVIEWING),
            MissionState.COMPLETED,
        )


def test_terminal_mission_cannot_resume() -> None:
    terminal = mission(
        MissionState.REVIEWING
    ).model_copy(
        update={
            "state": MissionState.COMPLETED,
            "outcome_id": "outcome-1",
        }
    )

    with pytest.raises(MissionStateError):
        transition_mission(
            terminal,
            MissionState.PLANNING,
        )