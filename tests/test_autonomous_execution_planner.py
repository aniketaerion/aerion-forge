from forge.autonomous_execution.planner import (
    AutonomousExecutionPlanner,
)
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
            objective="Plan execution.",
            repository_root="repository",
            requested_authority=AuthorityLevel.A2_MODIFY,
            requested_by="Aerion",
        ),
        state=MissionState.EXECUTING,
        granted_authority=AuthorityLevel.A2_MODIFY,
    )


def test_planner_builds_and_selects() -> None:
    step = MissionStep(
        step_id="step-1",
        plan_id="plan-1",
        sequence=1,
        title="Inspect repository",
        description="Inspect repository safely.",
        action_kind="read_file",
    )
    plan = MissionPlan(
        plan_id="plan-1",
        mission_id="mission-1",
        objective_summary="Inspect repository.",
        completion_criteria=("Inspection complete.",),
        steps=(step,),
    )

    planner = AutonomousExecutionPlanner()
    executable = planner.build(plan)
    selection = planner.select_next(
        mission(),
        plan,
        completed_step_ids=frozenset(),
    )

    assert executable.total_steps == 1
    assert selection.step is not None
    assert selection.step.step_id == "step-1"