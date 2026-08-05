from pathlib import Path

from forge.agent_runtime.models import (
    AgentCapability,
    AgentObjective,
    AgentRuntimeRequest,
    AgentSession,
    AgentSessionStatus,
    AgentStage,
)
from forge.agent_runtime.store import AgentRuntimeStore


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
        status=AgentSessionStatus.CREATED,
        stages=(stage,),
    )


def test_store_round_trip(tmp_path: Path) -> None:
    store = AgentRuntimeStore(tmp_path / "runtime")
    session = session_for()

    store.save_session(session)

    assert store.load_session(session.session_id) == session


def test_store_lists_sessions(tmp_path: Path) -> None:
    store = AgentRuntimeStore(tmp_path / "runtime")
    session = session_for()
    store.save_session(session)

    assert store.list_session_ids() == ("session-1",)