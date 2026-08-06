from forge.autonomous_execution.scheduler import next_eligible_step
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
            objective="Schedule execution steps.",
            repository_root="repository",
            requested_authority=AuthorityLevel.A2_MODIFY,
            requested_by="Aerion",
        ),
        state=MissionState.EXECUTING,
        granted_authority=AuthorityLevel.A2_MODIFY,
    )


def step(
    step_id: str,
    sequence: int,
    depends_on: tuple[str, ...] = (),
) -> MissionStep:
    return MissionStep(
        step_id=step_id,
        plan_id="plan-1",
        sequence=sequence,
        title=step_id,
        description=f"Execute {step_id}.",
        action_kind="read_file",
        depends_on=depends_on,
    )


def test_scheduler_selects_first_eligible_step() -> None:
    plan = MissionPlan(
        plan_id="plan-1",
        mission_id="mission-1",
        objective_summary="Execute steps.",
        completion_criteria=("All steps complete.",),
        steps=(
            step("step-2", 2, ("step-1",)),
            step("step-1", 1),
        ),
    )

    selected = next_eligible_step(
        mission(),
        plan,
        completed_step_ids=frozenset(),
    )

    assert selected is not None
    assert selected.step_id == "step-1"


def test_scheduler_advances_after_completion() -> None:
    plan = MissionPlan(
        plan_id="plan-1",
        mission_id="mission-1",
        objective_summary="Execute steps.",
        completion_criteria=("All steps complete.",),
        steps=(
            step("step-1", 1),
            step("step-2", 2, ("step-1",)),
        ),
    )

    selected = next_eligible_step(
        mission(),
        plan,
        completed_step_ids=frozenset({"step-1"}),
    )

    assert selected is not None
    assert selected.step_id == "step-2"