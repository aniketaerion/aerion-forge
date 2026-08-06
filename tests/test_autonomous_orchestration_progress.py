from forge.autonomous_orchestration.models import MissionSession
from forge.autonomous_orchestration.progress import evaluate_progress
from forge.autonomous_runtime.models import MissionPlan, MissionStep


def step(step_id: str, sequence: int) -> MissionStep:
    return MissionStep(
        step_id=step_id,
        plan_id="plan-1",
        sequence=sequence,
        title=step_id,
        description=f"Execute {step_id}.",
        action_kind="read_file",
    )


def test_progress_calculates_completion() -> None:
    plan = MissionPlan(
        plan_id="plan-1",
        mission_id="mission-1",
        objective_summary="Execute mission.",
        completion_criteria=("Mission complete.",),
        steps=(step("step-1", 1), step("step-2", 2)),
    )
    session = MissionSession(
        session_id="session-1",
        mission_id="mission-1",
        plan_id="plan-1",
        plan_version=1,
        repository_root="repository",
        completed_step_ids=("step-1",),
    )

    progress = evaluate_progress(session, plan)

    assert progress.completed_steps == 1
    assert progress.remaining_steps == 1
    assert progress.completion_percent == 50.0