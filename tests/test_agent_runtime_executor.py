from collections.abc import Mapping
from pathlib import Path
from typing import Any

from forge.agent_runtime.adapters.base import (
    AgentCapabilityAdapter,
    succeeded_result,
)
from forge.agent_runtime.executor import AgentRuntimeExecutor
from forge.agent_runtime.models import (
    AgentApproval,
    AgentCapability,
    AgentObjective,
    AgentRuntimePolicy,
    AgentRuntimeRequest,
    AgentSession,
    AgentSessionStatus,
    AgentStage,
    AgentStageResult,
    ApprovalKind,
)
from forge.agent_runtime.registry import AgentCapabilityRegistry


class SuccessAdapter(AgentCapabilityAdapter):
    capability = AgentCapability.MISSION_PLANNING

    def execute(
        self,
        repository_root: Path,
        session: AgentSession,
        stage: AgentStage,
        context: Mapping[str, Any],
    ) -> AgentStageResult:
        del repository_root, session, context
        return succeeded_result(stage, "planned")


def session_for(*, approved: bool) -> AgentSession:
    stage = AgentStage(
        stage_id="stage-1",
        sequence=1,
        capability=AgentCapability.MISSION_PLANNING,
        name="Plan",
        requires_approval=ApprovalKind.PLAN,
    )
    request = AgentRuntimeRequest(
        request_id="request-1",
        objective=AgentObjective(
            objective="Implement feature",
            repository_root=".",
        ),
    )
    approvals = (
        (
            AgentApproval(
                approval_id="approval-1",
                kind=ApprovalKind.PLAN,
                approved=True,
                approved_by="operator",
                reason="approved",
            ),
        )
        if approved
        else ()
    )
    return AgentSession(
        session_id="session-1",
        request=request,
        status=AgentSessionStatus.CREATED,
        stages=(stage,),
        approvals=approvals,
    )


def test_executor_stops_at_missing_approval(
    tmp_path: Path,
) -> None:
    registry = AgentCapabilityRegistry((SuccessAdapter(),))
    executor = AgentRuntimeExecutor(
        registry,
        AgentRuntimePolicy(),
    )

    updated = executor.run_next(
        session_for(approved=False),
        repository_root=tmp_path,
    )

    assert updated.status is AgentSessionStatus.AWAITING_APPROVAL
    assert not updated.stage_results


def test_executor_runs_approved_stage(tmp_path: Path) -> None:
    registry = AgentCapabilityRegistry((SuccessAdapter(),))
    executor = AgentRuntimeExecutor(
        registry,
        AgentRuntimePolicy(),
    )

    updated = executor.run_next(
        session_for(approved=True),
        repository_root=tmp_path,
    )

    assert len(updated.stage_results) == 1
    assert updated.stage_results[0].summary == "planned"