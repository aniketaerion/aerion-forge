from collections.abc import Mapping
from pathlib import Path
from typing import Any

from forge.agent_runtime.adapters.base import failed_result
from forge.agent_runtime.adapters.repair import RepairAdapter
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


def test_repair_adapter_can_return_failure(tmp_path: Path) -> None:
    def executor(
        repository_root: Path,
        session: AgentSession,
        stage: AgentStage,
        context: Mapping[str, Any],
    ) -> AgentStageResult:
        del repository_root, session, context
        return failed_result(stage, "repair exhausted")

    stage = AgentStage(
        stage_id="repair",
        sequence=1,
        capability=AgentCapability.AUTONOMOUS_REPAIR,
        name="Repair",
    )
    request = AgentRuntimeRequest(
        request_id="request-1",
        objective=AgentObjective(
            objective="Repair validation",
            repository_root=str(tmp_path),
        ),
    )
    session = AgentSession(
        session_id="session-1",
        request=request,
        status=AgentSessionStatus.REPAIRING,
        stages=(stage,),
    )

    result = RepairAdapter(executor).execute(
        tmp_path,
        session,
        stage,
        {},
    )

    assert result.status is AgentStageStatus.FAILED