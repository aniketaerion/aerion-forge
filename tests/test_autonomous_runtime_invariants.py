import pytest
from pydantic import ValidationError

from forge.autonomous_runtime.errors import MissionContractError
from forge.autonomous_runtime.invariants import (
    assert_budget_available,
    assert_execution_authority,
)
from forge.autonomous_runtime.models import (
    AutonomousMission,
    MissionRequest,
)
from forge.autonomous_runtime.states import (
    AuthorityLevel,
    MissionState,
)


def request() -> MissionRequest:
    return MissionRequest(
        request_id="request-1",
        objective="Control mission lifecycle.",
        repository_root="repository",
        requested_authority=AuthorityLevel.A2_MODIFY,
        requested_by="Aerion",
    )


def test_execution_requires_modify_authority() -> None:
    mission = AutonomousMission(
        mission_id="mission-1",
        request=request(),
        state=MissionState.EXECUTING,
        granted_authority=AuthorityLevel.A0_READ,
    )

    with pytest.raises(MissionContractError):
        assert_execution_authority(mission)


def test_budget_exhaustion_is_rejected() -> None:
    mission = AutonomousMission(
        mission_id="mission-2",
        request=request(),
        replan_count=3,
    )

    with pytest.raises(MissionContractError):
        assert_budget_available(mission)


def test_model_still_rejects_authority_above_request() -> None:
    with pytest.raises(ValidationError):
        AutonomousMission(
            mission_id="mission-3",
            request=request(),
            granted_authority=AuthorityLevel.A4_COMMIT,
        )