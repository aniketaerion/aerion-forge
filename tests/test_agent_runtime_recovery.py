import pytest

from forge.agent_runtime.errors import AgentRuntimeRecoveryError
from forge.agent_runtime.models import (
    AgentCapability,
    AgentCheckpoint,
    AgentObjective,
    AgentRuntimeRequest,
    AgentSession,
    AgentSessionStatus,
    AgentStage,
)
from forge.agent_runtime.recovery import recover_session


def session_for() -> AgentSession:
    stage = AgentStage(
        stage_id="stage-1",
        sequence=1,
        capability=AgentCapability.MISSION_PLANNING,
        name="Plan",
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
        status=AgentSessionStatus.PAUSED,
        stages=(stage,),
    )


def test_recovery_restores_checkpoint_state() -> None:
    session = session_for()
    checkpoint = AgentCheckpoint(
        checkpoint_id="checkpoint-1",
        session_id=session.session_id,
        status=AgentSessionStatus.PAUSED,
        repository_revision="abc",
    )

    recovered = recover_session(session, checkpoint)

    assert recovered.status is AgentSessionStatus.PAUSED


def test_recovery_rejects_foreign_checkpoint() -> None:
    session = session_for()
    checkpoint = AgentCheckpoint(
        checkpoint_id="checkpoint-1",
        session_id="other-session",
        status=AgentSessionStatus.PAUSED,
        repository_revision="abc",
    )

    with pytest.raises(AgentRuntimeRecoveryError):
        recover_session(session, checkpoint)