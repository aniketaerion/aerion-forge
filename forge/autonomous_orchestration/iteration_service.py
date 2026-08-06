"""Application service for one bounded orchestration iteration."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_execution.runtime import StepExecutionOutcome
from forge.autonomous_orchestration.identifiers import (
    orchestration_iteration_identifier,
)
from forge.autonomous_orchestration.journal import (
    InMemoryOrchestrationJournal,
    OrchestrationEvent,
)
from forge.autonomous_orchestration.models import (
    MissionSession,
    OrchestrationIteration,
    utc_now,
)
from forge.autonomous_orchestration.outcome_processor import (
    apply_outcome_to_session,
    classify_execution_outcome,
)
from forge.autonomous_orchestration.states import OrchestrationState
from forge.autonomous_orchestration.transitions import (
    assert_orchestration_transition,
)


@dataclass(slots=True)
class OrchestrationIterationService:
    """Process exactly one M5.2 execution outcome."""

    journal: InMemoryOrchestrationJournal

    def process(
        self,
        session: MissionSession,
        outcome: StepExecutionOutcome,
        *,
        mission_version_before: int,
        execution_request_id: str,
    ) -> tuple[MissionSession, OrchestrationIteration]:
        decision = classify_execution_outcome(outcome)

        assert_orchestration_transition(
            session.state,
            OrchestrationState.OUTCOME_PROCESSING,
        )

        processing = session.model_copy(
            update={
                "state": OrchestrationState.OUTCOME_PROCESSING,
                "version": session.version + 1,
                "updated_at": utc_now(),
            }
        )

        updated = apply_outcome_to_session(processing, outcome)

        sequence = updated.cycle_count + 1
        payload = {
            "session_id": updated.session_id,
            "sequence": sequence,
            "execution_id": outcome.record.execution_id,
            "outcome": decision.iteration_outcome.value,
        }

        iteration = OrchestrationIteration(
            iteration_id=orchestration_iteration_identifier(payload),
            session_id=updated.session_id,
            sequence=sequence,
            mission_version_before=mission_version_before,
            mission_version_after=mission_version_before + 1,
            selected_step_id=outcome.record.step_id,
            execution_request_id=execution_request_id,
            execution_id=outcome.record.execution_id,
            outcome=decision.iteration_outcome,
            evidence_ids=outcome.record.evidence_ids,
            completed_at=utc_now(),
        )

        event_sequence = len(
            self.journal.events_for(updated.session_id)
        ) + 1
        self.journal.append(
            OrchestrationEvent(
                event_id=(
                    f"{updated.session_id}-event-{event_sequence}"
                ),
                session_id=updated.session_id,
                sequence=event_sequence,
                event_type="execution_outcome_processed",
                previous_state=session.state,
                new_state=updated.state,
                payload={
                    "execution_id": outcome.record.execution_id,
                    "step_id": outcome.record.step_id,
                    "outcome": decision.iteration_outcome.value,
                },
            )
        )

        return updated, iteration