"""Process M5.2 execution outcomes into orchestration decisions."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_execution.runtime import StepExecutionOutcome
from forge.autonomous_execution.states import StepExecutionState
from forge.autonomous_orchestration.models import MissionSession, utc_now
from forge.autonomous_orchestration.states import (
    IterationOutcome,
    OrchestrationState,
)


@dataclass(frozen=True, slots=True)
class OutcomeDecision:
    """Decision derived from one M5.2 execution outcome."""

    iteration_outcome: IterationOutcome
    target_state: OrchestrationState
    step_completed: bool
    step_failed: bool
    reason: str


def classify_execution_outcome(
    outcome: StepExecutionOutcome,
) -> OutcomeDecision:
    """Classify an M5.2 outcome for orchestration."""
    state = outcome.record.state

    if state is StepExecutionState.SUCCEEDED:
        return OutcomeDecision(
            iteration_outcome=IterationOutcome.STEP_SUCCEEDED,
            target_state=OrchestrationState.PROGRESS_UPDATING,
            step_completed=True,
            step_failed=False,
            reason="Execution step succeeded.",
        )

    if state is StepExecutionState.FAILED:
        return OutcomeDecision(
            iteration_outcome=IterationOutcome.STEP_FAILED,
            target_state=OrchestrationState.RETRY_PENDING,
            step_completed=False,
            step_failed=True,
            reason="Execution step failed.",
        )

    if state is StepExecutionState.PAUSED:
        return OutcomeDecision(
            iteration_outcome=IterationOutcome.PAUSED,
            target_state=OrchestrationState.PAUSED,
            step_completed=False,
            step_failed=False,
            reason="Execution step paused.",
        )

    if state is StepExecutionState.ESCALATED:
        return OutcomeDecision(
            iteration_outcome=IterationOutcome.ESCALATED,
            target_state=OrchestrationState.ESCALATED,
            step_completed=False,
            step_failed=False,
            reason="Execution step escalated.",
        )

    return OutcomeDecision(
        iteration_outcome=IterationOutcome.STEP_FAILED,
        target_state=OrchestrationState.FAILED,
        step_completed=False,
        step_failed=True,
        reason=f"Unsupported execution state: {state.value}.",
    )


def apply_outcome_to_session(
    session: MissionSession,
    outcome: StepExecutionOutcome,
) -> MissionSession:
    """Update session progress from one execution outcome."""
    decision = classify_execution_outcome(outcome)
    step_id = outcome.record.step_id

    completed = set(session.completed_step_ids)
    failed = set(session.failed_step_ids)

    if decision.step_completed:
        completed.add(step_id)
        failed.discard(step_id)

    if decision.step_failed:
        failed.add(step_id)

    return session.model_copy(
        update={
            "current_step_id": (
                None if decision.step_completed else step_id
            ),
            "completed_step_ids": tuple(sorted(completed)),
            "failed_step_ids": tuple(sorted(failed)),
            "execution_count": session.execution_count + 1,
            "state": decision.target_state,
            "version": session.version + 1,
            "updated_at": utc_now(),
            "stop_reason": (
                decision.reason
                if decision.target_state
                in {
                    OrchestrationState.FAILED,
                    OrchestrationState.PAUSED,
                    OrchestrationState.ESCALATED,
                }
                else session.stop_reason
            ),
        }
    )