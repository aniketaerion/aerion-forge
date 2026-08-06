from forge.autonomous_execution.eligibility import (
    evaluate_step_eligibility,
)
from forge.autonomous_runtime.models import (
    AutonomousMission,
    MissionRequest,
    MissionStep,
)
from forge.autonomous_runtime.states import (
    AuthorityLevel,
    MissionState,
)


def mission(
    state: MissionState = MissionState.EXECUTING,
) -> AutonomousMission:
    return AutonomousMission(
        mission_id="mission-1",
        request=MissionRequest(
            request_id="request-1",
            objective="Execute approved steps.",
            repository_root="repository",
            requested_authority=AuthorityLevel.A2_MODIFY,
            requested_by="Aerion",
        ),
        state=state,
        granted_authority=AuthorityLevel.A2_MODIFY,
    )


def step() -> MissionStep:
    return MissionStep(
        step_id="step-1",
        plan_id="plan-1",
        sequence=1,
        title="Inspect repository",
        description="Inspect repository safely.",
        action_kind="read_file",
    )


def test_step_is_eligible_for_executing_mission() -> None:
    result = evaluate_step_eligibility(
        mission(),
        step(),
        completed_step_ids=frozenset(),
    )

    assert result.eligible


def test_step_is_not_eligible_outside_execution_state() -> None:
    result = evaluate_step_eligibility(
        mission(MissionState.PLANNING),
        step(),
        completed_step_ids=frozenset(),
    )

    assert not result.eligible
    assert "Mission is not in executing state." in result.reasons