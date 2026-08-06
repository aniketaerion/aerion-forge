"""Controlled runtime for one autonomous execution step."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_execution.evidence import (
    build_execution_evidence,
)
from forge.autonomous_execution.execution_journal import (
    ExecutionEvent,
    InMemoryExecutionJournal,
)
from forge.autonomous_execution.execution_transitions import (
    assert_execution_transition,
)
from forge.autonomous_execution.identifiers import (
    step_execution_identifier,
)
from forge.autonomous_execution.lease_manager import (
    InMemoryExecutionLeaseManager,
)
from forge.autonomous_execution.models import (
    ExecutionEvidence,
    ExecutionRequest,
    StepExecutionRecord,
    utc_now,
)
from forge.autonomous_execution.policies import (
    AutonomousExecutionPolicy,
)
from forge.autonomous_execution.states import (
    ExecutionFailureClass,
    StepExecutionState,
    ToolExecutionStatus,
)
from forge.autonomous_execution.tool_contracts import (
    ToolExecutionRequest,
)
from forge.autonomous_execution.tool_gateway import (
    ControlledToolGateway,
)


@dataclass(frozen=True, slots=True)
class StepExecutionOutcome:
    """Final result of one bounded execution attempt."""

    record: StepExecutionRecord
    evidence: tuple[ExecutionEvidence, ...]


@dataclass(slots=True)
class AutonomousExecutionRuntime:
    """Execute one approved step through the controlled gateway."""

    gateway: ControlledToolGateway
    leases: InMemoryExecutionLeaseManager
    journal: InMemoryExecutionJournal
    policy: AutonomousExecutionPolicy

    def _event(
        self,
        *,
        execution_id: str,
        previous: StepExecutionState | None,
        new: StepExecutionState,
        event_type: str,
    ) -> None:
        sequence = len(self.journal.events_for(execution_id)) + 1
        self.journal.append(
            ExecutionEvent(
                event_id=f"{execution_id}-event-{sequence}",
                execution_id=execution_id,
                sequence=sequence,
                event_type=event_type,
                previous_state=previous,
                new_state=new,
            )
        )

    def execute(
        self,
        request: ExecutionRequest,
        tool_request: ToolExecutionRequest,
        *,
        repository_fingerprint: str,
        holder: str = "autonomous-runtime",
    ) -> StepExecutionOutcome:
        execution_id = step_execution_identifier(
            {
                "mission_id": request.mission_id,
                "step_id": request.step_id,
                "request_id": request.request_id,
            }
        )
        state = StepExecutionState.PENDING
        self._event(
            execution_id=execution_id,
            previous=None,
            new=state,
            event_type="execution_created",
        )

        transitions = (
            StepExecutionState.ELIGIBILITY_CHECK,
            StepExecutionState.READY,
            StepExecutionState.LEASE_ACQUIRING,
        )
        for target in transitions:
            assert_execution_transition(state, target)
            previous = state
            state = target
            self._event(
                execution_id=execution_id,
                previous=previous,
                new=state,
                event_type="execution_state_changed",
            )

        lease = self.leases.acquire(
            mission_id=request.mission_id,
            repository_root=request.repository_root,
            holder=holder,
            lease_seconds=(
                self.policy.budgets.maximum_lease_seconds
            ),
        )

        for target in (
            StepExecutionState.CHECKPOINT_VERIFYING,
            StepExecutionState.TOOL_PREPARING,
            StepExecutionState.TOOL_RUNNING,
        ):
            assert_execution_transition(state, target)
            previous = state
            state = target
            self._event(
                execution_id=execution_id,
                previous=previous,
                new=state,
                event_type="execution_state_changed",
            )

        result = self.gateway.execute(tool_request)

        if result.status not in {
            ToolExecutionStatus.SUCCEEDED,
            ToolExecutionStatus.DRY_RUN,
        }:
            completed_at = utc_now()
            record = StepExecutionRecord(
                execution_id=execution_id,
                mission_id=request.mission_id,
                step_id=request.step_id,
                lease_id=lease.lease_id,
                checkpoint_id=tool_request.checkpoint_id,
                invocation_results=(result,),
                state=StepExecutionState.FAILED,
                failure_class=ExecutionFailureClass.TOOL_EXIT_FAILURE,
                completed_at=completed_at,
            )
            self.leases.release(lease)
            return StepExecutionOutcome(
                record=record,
                evidence=(),
            )

        for target in (
            StepExecutionState.EFFECT_VERIFYING,
            StepExecutionState.EVIDENCE_RECORDING,
        ):
            assert_execution_transition(state, target)
            previous = state
            state = target
            self._event(
                execution_id=execution_id,
                previous=previous,
                new=state,
                event_type="execution_state_changed",
            )

        evidence = build_execution_evidence(
            execution_id=execution_id,
            result=result,
            repository_fingerprint=repository_fingerprint,
        )

        assert_execution_transition(
            state,
            StepExecutionState.SUCCEEDED,
        )
        previous = state
        state = StepExecutionState.SUCCEEDED
        self._event(
            execution_id=execution_id,
            previous=previous,
            new=state,
            event_type="execution_succeeded",
        )

        record = StepExecutionRecord(
            execution_id=execution_id,
            mission_id=request.mission_id,
            step_id=request.step_id,
            lease_id=lease.lease_id,
            checkpoint_id=tool_request.checkpoint_id,
            invocation_results=(result,),
            evidence_ids=(evidence.evidence_id,),
            state=StepExecutionState.SUCCEEDED,
            completed_at=utc_now(),
        )
        self.leases.release(lease)

        return StepExecutionOutcome(
            record=record,
            evidence=(evidence,),
        )