from collections.abc import Mapping
from pathlib import Path
from typing import Any

from forge.agent_runtime.adapters.base import succeeded_result
from forge.agent_runtime.adapters.planning import PlanningAdapter
from forge.agent_runtime.models import (
    AgentCapability,
    AgentObjective,
    AgentRuntimeRequest,
    AgentSession,
    AgentSessionStatus,
    AgentStage,
    AgentStageResult,
)


def test_planning_adapter_executes_callback(tmp_path: Path) -> None:
    observed: dict[str, str] = {}

    def executor(
        repository_root: Path,
        session: AgentSession,
        stage: AgentStage,
        context: Mapping[str, Any],
    ) -> AgentStageResult:
        del session, context
        observed["root"] = str(repository_root)
        return succeeded_result(stage, "mission plan created")

    stage = AgentStage(
        stage_id="planning",
        sequence=1,
        capability=AgentCapability.MISSION_PLANNING,
        name="Planning",
    )
    request = AgentRuntimeRequest(
        request_id="request-1",
        objective=AgentObjective(
            objective="Implement feature",
            repository_root=str(tmp_path),
        ),
    )
    session = AgentSession(
        session_id="session-1",
        request=request,
        status=AgentSessionStatus.PLANNING,
        stages=(stage,),
    )

    result = PlanningAdapter(executor).execute(
        tmp_path,
        session,
        stage,
        {},
    )

    assert result.summary == "mission plan created"
    assert observed["root"] == str(tmp_path.resolve())