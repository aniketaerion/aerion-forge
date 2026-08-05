from collections.abc import Mapping
from pathlib import Path
from typing import Any

from forge.agent_runtime.adapters.base import succeeded_result
from forge.agent_runtime.adapters.impact import ImpactAdapter
from forge.agent_runtime.models import (
    AgentCapability,
    AgentObjective,
    AgentRuntimeRequest,
    AgentSession,
    AgentSessionStatus,
    AgentStage,
    AgentStageResult,
)


def test_impact_adapter_normalizes_result(tmp_path: Path) -> None:
    def executor(
        repository_root: Path,
        session: AgentSession,
        stage: AgentStage,
        context: Mapping[str, Any],
    ) -> AgentStageResult:
        del repository_root, session, context
        return succeeded_result(
            stage,
            "impact analysed",
            evidence={"risk": "low"},
        )

    stage = AgentStage(
        stage_id="impact",
        sequence=1,
        capability=AgentCapability.IMPACT_ANALYSIS,
        name="Impact",
    )
    request = AgentRuntimeRequest(
        request_id="request-1",
        objective=AgentObjective(
            objective="Analyse impact",
            repository_root=str(tmp_path),
        ),
    )
    session = AgentSession(
        session_id="session-1",
        request=request,
        status=AgentSessionStatus.EXECUTING,
        stages=(stage,),
    )

    result = ImpactAdapter(executor).execute(
        tmp_path,
        session,
        stage,
        {},
    )

    assert result.evidence["risk"] == "low"