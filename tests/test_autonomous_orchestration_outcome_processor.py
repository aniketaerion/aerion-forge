from forge.autonomous_execution.models import (
    StepExecutionRecord,
    utc_now,
)
from forge.autonomous_execution.runtime import StepExecutionOutcome
from forge.autonomous_execution.states import StepExecutionState
from forge.autonomous_orchestration.models import MissionSession
from forge.autonomous_orchestration.outcome_processor import (
    apply_outcome_to_session,
    classify_execution_outcome,
)
from forge.autonomous_orchestration.states import (
    IterationOutcome,
    OrchestrationState,
)


def successful_outcome() -> StepExecutionOutcome:
    return StepExecutionOutcome(
        record=StepExecutionRecord(
            execution_id="execution-1",
            mission_id="mission-1",
            step_id="step-1",
            state=StepExecutionState.SUCCEEDED,
            evidence_ids=("evidence-1",),
            completed_at=utc_now(),
        ),
        evidence=(),
    )


def test_successful_outcome_is_classified() -> None:
    decision = classify_execution_outcome(successful_outcome())

    assert decision.iteration_outcome is IterationOutcome.STEP_SUCCEEDED
    assert decision.step_completed


def test_successful_outcome_updates_session() -> None:
    session = MissionSession(
        session_id="session-1",
        mission_id="mission-1",
        plan_id="plan-1",
        plan_version=1,
        repository_root="repository",
        state=OrchestrationState.OUTCOME_PROCESSING,
        current_step_id="step-1",
    )

    updated = apply_outcome_to_session(
        session,
        successful_outcome(),
    )

    assert updated.completed_step_ids == ("step-1",)
    assert updated.current_step_id is None
    assert updated.execution_count == 1