from forge.autonomous_execution.planner import (
    AutonomousExecutionPlanner,
)
from forge.autonomous_orchestration.coordinator import (
    MissionStepCoordinator,
)
from forge.autonomous_orchestration.models import (
    MissionSession,
    OrchestrationRequest,
)
from forge.autonomous_orchestration.plan_loader import (
    InMemoryApprovedPlanStore,
)
from forge.autonomous_orchestration.policies import (
    AutonomousOrchestrationPolicy,
)
from forge.autonomous_orchestration.states import IterationOutcome
from forge.autonomous_runtime.models import (
    AutonomousMission,
    MissionPlan,
    MissionRequest,
    MissionStep,
)
from forge.autonomous_runtime.states import (
    AuthorityLevel,
    MissionState,
)


def mission() -> AutonomousMission:
    return AutonomousMission(
        mission_id="mission-1",
        request=MissionRequest(
            request_id="request-1",
            objective="Execute mission.",
            repository_root="repository",
            requested_authority=AuthorityLevel.A2_MODIFY,
            requested_by="Aerion",
        ),
        state=MissionState.EXECUTING,
        granted_authority=AuthorityLevel.A2_MODIFY,
    )


def test_coordinator_selects_one_step() -> None:
    plan = MissionPlan(
        plan_id="plan-1",
        mission_id="mission-1",
        objective_summary="Execute mission.",
        completion_criteria=("Mission complete.",),
        steps=(
            MissionStep(
                step_id="step-1",
                plan_id="plan-1",
                sequence=1,
                title="Inspect repository",
                description="Inspect repository.",
                action_kind="read_file",
            ),
        ),
    )
    store = InMemoryApprovedPlanStore()
    store.register(plan)

    coordinator = MissionStepCoordinator(
        plan_store=store,
        planner=AutonomousExecutionPlanner(),
        policy=AutonomousOrchestrationPolicy(),
    )
    session = MissionSession(
        session_id="session-1",
        mission_id="mission-1",
        plan_id="plan-1",
        plan_version=1,
        repository_root="repository",
    )

    result = coordinator.coordinate(
        OrchestrationRequest(
            request_id="orchestration-request-1",
            mission_id="mission-1",
            repository_root="repository",
            requested_by="Aerion",
        ),
        session,
        mission(),
    )

    assert result.selected_step_id == "step-1"
    assert result.execution_request_id is not None
    assert result.iteration.outcome is IterationOutcome.STEP_SELECTED
    assert result.session.current_step_id == "step-1"