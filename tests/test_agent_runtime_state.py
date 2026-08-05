from datetime import UTC, datetime

import pytest

from forge.agent_runtime.errors import AgentRuntimeStateError
from forge.agent_runtime.models import (
    AgentCapability,
    AgentObjective,
    AgentRuntimeRequest,
    AgentSession,
    AgentSessionStatus,
    AgentStage,
    AgentStageResult,
    AgentStageStatus,
)
from forge.agent_runtime.state import (
    append_stage_result,
    can_transition,
    next_ready_stage,
    transition_session,
)


def session_for() -> AgentSession:
    first = AgentStage(
        stage_id="stage-1",
        sequence=1,
        capability=AgentCapability.MISSION_PLANNING,
        name="Plan",
    )
    second = AgentStage(
        stage_id="stage-2",
        sequence=2,
        capability=AgentCapability.IMPACT_ANALYSIS,
        name="Impact",
        depends_on=("stage-1",),
    )
    request = AgentRuntimeRequest(
        request_id="request-1",
        objective=AgentObjective(
            objective="Implement feature",
            repository_root=".",
        ),
    )
    return AgentSession(
        session_id="session-1",
        request=request,
        status=AgentSessionStatus.CREATED,
        stages=(first, second),
    )


def test_valid_transition_is_allowed() -> None:
    assert can_transition(
        AgentSessionStatus.CREATED,
        AgentSessionStatus.PLANNING,
    )


def test_invalid_transition_is_rejected() -> None:
    with pytest.raises(AgentRuntimeStateError):
        transition_session(
            session_for(),
            AgentSessionStatus.COMPLETED,
        )


def test_next_ready_stage_respects_dependencies() -> None:
    session = session_for()

    stage = next_ready_stage(session)
    assert stage is not None
    assert stage.stage_id == "stage-1"

    completed = AgentStageResult(
        stage_id="stage-1",
        status=AgentStageStatus.SUCCEEDED,
        summary="done",
        completed_at=datetime.now(UTC),
    )
    updated = append_stage_result(session, completed)

    stage = next_ready_stage(updated)
    assert stage is not None
    assert stage.stage_id == "stage-2"


def test_duplicate_stage_result_is_rejected() -> None:
    session = session_for()
    result = AgentStageResult(
        stage_id="stage-1",
        status=AgentStageStatus.SUCCEEDED,
        summary="done",
        completed_at=datetime.now(UTC),
    )
    updated = append_stage_result(session, result)

    with pytest.raises(AgentRuntimeStateError):
        append_stage_result(updated, result)