from collections.abc import Mapping
from pathlib import Path
from typing import Any

from forge.agent_runtime.adapters.base import succeeded_result
from forge.agent_runtime.adapters.editing import EditingAdapter
from forge.agent_runtime.models import (
    AgentCapability,
    AgentObjective,
    AgentRuntimeRequest,
    AgentSession,
    AgentSessionStatus,
    AgentStage,
    AgentStageResult,
)


def test_editing_adapter_preserves_stage_identity(
    tmp_path: Path,
) -> None:
    def executor(
        repository_root: Path,
        session: AgentSession,
        stage: AgentStage,
        context: Mapping[str, Any],
    ) -> AgentStageResult:
        del repository_root, session, context
        return succeeded_result(stage, "edit applied")

    stage = AgentStage(
        stage_id="edit",
        sequence=1,
        capability=AgentCapability.SAFE_CODE_EDITING,
        name="Edit",
    )
    request = AgentRuntimeRequest(
        request_id="request-1",
        objective=AgentObjective(
            objective="Apply edit",
            repository_root=str(tmp_path),
        ),
    )
    session = AgentSession(
        session_id="session-1",
        request=request,
        status=AgentSessionStatus.EXECUTING,
        stages=(stage,),
    )

    result = EditingAdapter(executor).execute(
        tmp_path,
        session,
        stage,
        {},
    )

    assert result.stage_id == stage.stage_id