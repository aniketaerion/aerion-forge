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
from forge.mission_runtime.execution_conversion import (
    execution_request_from_plan,
    execution_run_from_plan,
)
from forge.mission_runtime.models import MissionRequest
from forge.workspace.models import (
    ProjectType,
    WorkspaceHealth,
    WorkspaceStatus,
)


def context() -> MissionEngineeringContext:
    return MissionEngineeringContext(
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


def plan() -> PlanningPlan:
    return PlanningPlan(
        plan_id="plan-1",
        request_id="planning-request-1",
        summary="Implement approved change.",
        steps=(
            PlanningStep(
                step_id="planning-step-1",
                sequence=1,
                name="Edit code",
                description="Apply approved code change.",
                kind=StepKind.CODE_CHANGE,
                required_tools=("filesystem",),
                risk=PlanningRisk.LOW,
            ),
        ),
    )


def test_plan_converts_to_execution_run() -> None:
    request = MissionRequest(
        request_id="mission-request-1",
        workspace_id="workspace-1",
        repository_root="repository",
        statement="Implement approved change.",
        requested_by="Aerion",
    )

    execution_request = execution_request_from_plan(
        request=request,
        context=context(),
        plan=plan(),
        repository_fingerprint="fingerprint-1",
    )
    run = execution_run_from_plan(
        execution_request=execution_request,
        plan=plan(),
    )

    assert run.plan_id == "plan-1"
    assert run.repository_fingerprint == "fingerprint-1"
    assert len(run.steps) == 1
    assert run.steps[0].planning_step_id == "planning-step-1"
    assert run.steps[0].required_tools == ("filesystem",)