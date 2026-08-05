from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

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


def test_objective_rejects_repository_escape() -> None:
    with pytest.raises(ValidationError):
        AgentObjective(
            objective="Modify repository",
            repository_root=".",
            target_paths=("../outside.py",),
        )


def test_session_rejects_duplicate_stage_ids() -> None:
    stage = AgentStage(
        stage_id="stage-1",
        sequence=1,
        capability=AgentCapability.MISSION_PLANNING,
        name="Plan mission",
    )
    request = AgentRuntimeRequest(
        request_id="request-1",
        objective=AgentObjective(
            objective="Implement feature",
            repository_root=".",
        ),
    )

    with pytest.raises(ValidationError):
        AgentSession(
            session_id="session-1",
            request=request,
            status=AgentSessionStatus.CREATED,
            stages=(stage, stage),
        )


def test_session_rejects_unknown_stage_dependency() -> None:
    stage = AgentStage(
        stage_id="stage-1",
        sequence=1,
        capability=AgentCapability.MISSION_PLANNING,
        name="Plan mission",
        depends_on=("missing-stage",),
    )
    request = AgentRuntimeRequest(
        request_id="request-1",
        objective=AgentObjective(
            objective="Implement feature",
            repository_root=".",
        ),
    )

    with pytest.raises(ValidationError):
        AgentSession(
            session_id="session-1",
            request=request,
            status=AgentSessionStatus.CREATED,
            stages=(stage,),
        )


def test_terminal_stage_result_requires_completion_time() -> None:
    with pytest.raises(ValidationError):
        AgentStageResult(
            stage_id="stage-1",
            status=AgentStageStatus.SUCCEEDED,
            summary="completed",
        )


def test_terminal_stage_result_accepts_completion_time() -> None:
    result = AgentStageResult(
        stage_id="stage-1",
        status=AgentStageStatus.SUCCEEDED,
        summary="completed",
        completed_at=datetime.now(UTC),
    )

    assert result.status is AgentStageStatus.SUCCEEDED