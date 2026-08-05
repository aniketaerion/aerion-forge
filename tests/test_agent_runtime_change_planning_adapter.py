from collections.abc import Mapping
from pathlib import Path
from typing import Any

from forge.agent_runtime.adapters.base import succeeded_result
from forge.agent_runtime.adapters.change_planning import (
    ChangePlanningAdapter,
)
from forge.agent_runtime.models import (
    AgentCapability,
    AgentObjective,
    AgentRuntimeRequest,
    AgentSession,
    AgentSessionStatus,
    AgentStage,
    AgentStageResult,
)


def test_change_planning_adapter_returns_artifacts(
    tmp_path: Path,
) -> None:
    def executor(
        repository_root: Path,
        session: AgentSession,
        stage: AgentStage,
        context: Mapping[str, Any],
    ) -> AgentStageResult:
        del repository_root, session, context
        return succeeded_result(
            stage,
            "change plan created",
            artifact_paths=("reports/change-plan.json",),
        )

    stage = AgentStage(
        stage_id="change-plan",
        sequence=1,
        capability=AgentCapability.SAFE_CHANGE_PLANNING,
        name="Change plan",
    )
    request = AgentRuntimeRequest(
        request_id="request-1",
        objective=AgentObjective(
            objective="Plan changes",
            repository_root=str(tmp_path),
        ),
    )
    session = AgentSession(
        session_id="session-1",
        request=request,
        status=AgentSessionStatus.PLANNING,
        stages=(stage,),
    )

    result = ChangePlanningAdapter(executor).execute(
        tmp_path,
        session,
        stage,
        {},
    )

    assert result.artifact_paths == ("reports/change-plan.json",)