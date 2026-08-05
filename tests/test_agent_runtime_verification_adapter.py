from collections.abc import Mapping
from pathlib import Path
from typing import Any

from forge.agent_runtime.adapters.base import succeeded_result
from forge.agent_runtime.adapters.verification import VerificationAdapter
from forge.agent_runtime.models import (
    AgentCapability,
    AgentObjective,
    AgentRuntimeRequest,
    AgentSession,
    AgentSessionStatus,
    AgentStage,
    AgentStageResult,
)


def test_verification_adapter_returns_release_evidence(
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
            "release approved",
            evidence={"decision": "approved"},
        )

    stage = AgentStage(
        stage_id="verification",
        sequence=1,
        capability=AgentCapability.BUILD_VERIFICATION,
        name="Verification",
    )
    request = AgentRuntimeRequest(
        request_id="request-1",
        objective=AgentObjective(
            objective="Verify release",
            repository_root=str(tmp_path),
        ),
    )
    session = AgentSession(
        session_id="session-1",
        request=request,
        status=AgentSessionStatus.VERIFYING,
        stages=(stage,),
    )

    result = VerificationAdapter(executor).execute(
        tmp_path,
        session,
        stage,
        {},
    )

    assert result.evidence["decision"] == "approved"