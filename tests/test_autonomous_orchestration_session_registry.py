import pytest

from forge.autonomous_orchestration.errors import (
    OrchestrationContractError,
)
from forge.autonomous_orchestration.models import MissionSession
from forge.autonomous_orchestration.session_registry import (
    InMemorySessionRegistry,
)
from forge.autonomous_orchestration.states import OrchestrationState


def session(
    session_id: str,
    *,
    version: int = 1,
    state: OrchestrationState = OrchestrationState.CREATED,
) -> MissionSession:
    return MissionSession(
        session_id=session_id,
        mission_id="mission-1",
        plan_id="plan-1",
        plan_version=1,
        repository_root="repository",
        version=version,
        state=state,
        stop_reason=(
            "Complete."
            if state is OrchestrationState.COMPLETED
            else None
        ),
    )


def test_only_one_active_session_per_mission() -> None:
    registry = InMemorySessionRegistry()
    registry.create(session("session-1"))

    with pytest.raises(OrchestrationContractError):
        registry.create(session("session-2"))


def test_update_requires_matching_version() -> None:
    registry = InMemorySessionRegistry()
    registry.create(session("session-1"))

    with pytest.raises(OrchestrationContractError):
        registry.update(
            session("session-1", version=3),
            expected_version=1,
        )