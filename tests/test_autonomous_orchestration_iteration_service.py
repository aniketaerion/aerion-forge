from forge.autonomous_execution.models import (
    StepExecutionRecord,
    utc_now,
)
from forge.autonomous_execution.runtime import StepExecutionOutcome
from forge.autonomous_execution.states import StepExecutionState
from forge.autonomous_orchestration.iteration_service import (
    OrchestrationIterationService,
)
from forge.autonomous_orchestration.journal import (
    InMemoryOrchestrationJournal,
)
from forge.autonomous_orchestration.models import MissionSession
from forge.autonomous_orchestration.states import (
    IterationOutcome,
    OrchestrationState,
)


def test_iteration_service_processes_one_outcome() -> None:
    service = OrchestrationIterationService(
        journal=InMemoryOrchestrationJournal()
    )
    session = MissionSession(
        session_id="session-1",
        mission_id="mission-1",
        plan_id="plan-1",
        plan_version=1,
        repository_root="repository",
        state=OrchestrationState.STEP_EXECUTING,
        current_step_id="step-1",
    )
    outcome = StepExecutionOutcome(
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

    updated, iteration = service.process(
        session,
        outcome,
        mission_version_before=1,
        execution_request_id="execution-request-1",
    )

    assert updated.completed_step_ids == ("step-1",)
    assert iteration.outcome is IterationOutcome.STEP_SUCCEEDED
    assert iteration.execution_request_id == "execution-request-1"
