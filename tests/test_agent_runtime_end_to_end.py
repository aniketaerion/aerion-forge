from collections.abc import Mapping
from pathlib import Path
from typing import Any

from forge.agent_runtime.adapters.base import (
    AgentCapabilityAdapter,
    succeeded_result,
)
from forge.agent_runtime.models import (
    AgentApproval,
    AgentCapability,
    AgentObjective,
    AgentRuntimePolicy,
    AgentSession,
    AgentSessionStatus,
    AgentStage,
    AgentStageResult,
    ApprovalKind,
)
from forge.agent_runtime.registry import AgentCapabilityRegistry
from forge.agent_runtime.service import AgentRuntimeService


class PlanningAdapter(AgentCapabilityAdapter):
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


def test_agent_runtime_end_to_end(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    service = AgentRuntimeService(
        AgentCapabilityRegistry((PlanningAdapter(),)),
        AgentRuntimePolicy(
            allowed_capabilities=(
                AgentCapability.MISSION_PLANNING,
            )
        ),
    )
    request = service.create_request(
        AgentObjective(
            objective="Plan feature",
            repository_root=str(tmp_path),
            requested_capabilities=(
                AgentCapability.MISSION_PLANNING,
            ),
        )
    )
    session = service.create_session(request)
    approved = service.add_approval(
        session,
        AgentApproval(
            approval_id="approval-1",
            kind=ApprovalKind.PLAN,
            approved=True,
            approved_by="operator",
            reason="approved",
        ),
    )

    completed = service.run_to_boundary(approved)

    assert completed.status is AgentSessionStatus.COMPLETED
    assert len(completed.stage_results) == 1

def test_agent_runtime_resumes_after_plan_approval(
    tmp_path: Path,
) -> None:
    (tmp_path / ".git").mkdir()
    service = AgentRuntimeService(
        AgentCapabilityRegistry((PlanningAdapter(),)),
        AgentRuntimePolicy(
            allowed_capabilities=(
                AgentCapability.MISSION_PLANNING,
            )
        ),
    )
    request = service.create_request(
        AgentObjective(
            objective="Plan feature",
            repository_root=str(tmp_path),
            requested_capabilities=(
                AgentCapability.MISSION_PLANNING,
            ),
        )
    )
    session = service.create_session(request)

    awaiting_approval = service.run_to_boundary(session)

    assert (
        awaiting_approval.status
        is AgentSessionStatus.AWAITING_APPROVAL
    )
    assert len(awaiting_approval.stage_results) == 0

    approved = service.add_approval(
        awaiting_approval,
        AgentApproval(
            approval_id="approval-resume-1",
            kind=ApprovalKind.PLAN,
            approved=True,
            approved_by="operator",
            reason="approved",
        ),
    )

    completed = service.run_to_boundary(approved)

    assert completed.status is AgentSessionStatus.COMPLETED
    assert len(completed.stage_results) == 1
    assert completed.stage_results[0].summary == "planned"