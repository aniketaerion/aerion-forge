from forge.autonomous_planning.models import (
    PlanningPlan,
    PlanningStep,
)
from forge.autonomous_planning.states import (
    PlanningRisk,
    StepKind,
)
from forge.mission_runtime.context import (
    MissionCapabilitySelection,
    MissionEngineeringContext,
    MissionTechnologyContext,
    MissionWorkspaceContext,
)
from forge.mission_runtime.execution_authority import (
    execution_authority_for_plan,
)
from forge.mission_runtime.models import (
    MissionApproval,
    MissionRequest,
)
from forge.mission_runtime.states import (
    MissionApprovalDecision,
    MissionApprovalKind,
)
from forge.workspace.models import (
    ProjectType,
    WorkspaceHealth,
    WorkspaceStatus,
)


def test_approved_plan_grants_explicit_authority() -> None:
    context = MissionEngineeringContext(
        workspace=MissionWorkspaceContext(
            workspace_id="workspace-1",
            workspace_name="ERP",
            repository_root="repository",
            status=WorkspaceStatus.READY,
            health=WorkspaceHealth.HEALTHY,
            technology=MissionTechnologyContext(
                project_type=ProjectType.ERP,
            ),
        ),
        capabilities=MissionCapabilitySelection(
            capability_ids=("safe-code-editing",),
        ),
    )
    request = MissionRequest(
        request_id="request-1",
        workspace_id="workspace-1",
        repository_root="repository",
        statement="Implement approved change.",
        requested_by="Aerion",
    )
    plan = PlanningPlan(
        plan_id="plan-1",
        request_id="planning-request-1",
        summary="Approved plan.",
        steps=(
            PlanningStep(
                step_id="step-1",
                sequence=1,
                name="Edit",
                description="Edit approved source.",
                kind=StepKind.CODE_CHANGE,
                required_tools=("filesystem",),
                risk=PlanningRisk.HIGH,
            ),
        ),
    )
    approval = MissionApproval(
        approval_id="approval-1",
        session_id="session-1",
        kind=MissionApprovalKind.PLAN,
        decision=MissionApprovalDecision.APPROVED,
        decided_by="reviewer",
        rationale="Approved.",
    )

    authority = execution_authority_for_plan(
        request=request,
        context=context,
        plan=plan,
        approval=approval,
    )

    assert authority.subject == "Aerion"
    assert authority.permitted_tools == ("filesystem",)
    assert authority.high_risk_approved