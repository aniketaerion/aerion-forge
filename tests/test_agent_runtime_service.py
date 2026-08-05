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


def initialize_repository(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()


def test_service_creates_deterministic_session(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)
    registry = AgentCapabilityRegistry((PlanningAdapter(),))
    policy = AgentRuntimePolicy(
        allowed_capabilities=(
            AgentCapability.MISSION_PLANNING,
        )
    )
    service = AgentRuntimeService(registry, policy)
    objective = AgentObjective(
        objective="Plan feature",
        repository_root=str(tmp_path),
        requested_capabilities=(
            AgentCapability.MISSION_PLANNING,
        ),
    )

    request = service.create_request(objective)
    first = service.create_session(request)
    second = service.create_session(request)

    assert first.session_id == second.session_id
    assert first.stages == second.stages


def test_service_runs_session_to_completion(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)
    registry = AgentCapabilityRegistry((PlanningAdapter(),))
    policy = AgentRuntimePolicy(
        allowed_capabilities=(
            AgentCapability.MISSION_PLANNING,
        )
    )
    service = AgentRuntimeService(registry, policy)
    objective = AgentObjective(
        objective="Plan feature",
        repository_root=str(tmp_path),
        requested_capabilities=(
            AgentCapability.MISSION_PLANNING,
        ),
    )
    request = service.create_request(objective)
    session = service.create_session(request)
    approval = AgentApproval(
        approval_id="approval-1",
        kind=ApprovalKind.PLAN,
        approved=True,
        approved_by="operator",
        reason="approved",
    )
    approved = service.add_approval(session, approval)

    executed = service.run_to_boundary(approved)
    completed = service.run_to_boundary(executed)

    assert completed.status is AgentSessionStatus.COMPLETED
    assert len(completed.stage_results) == 1