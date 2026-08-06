[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

function Write-Utf8NoBom {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$Content
    )

    $FullPath = Join-Path $RepositoryRoot $Path
    $Directory = Split-Path $FullPath -Parent

    New-Item `
        -ItemType Directory `
        -Path $Directory `
        -Force | Out-Null

    [System.IO.File]::WriteAllText(
        $FullPath,
        $Content,
        [System.Text.UTF8Encoding]::new($false)
    )

    Write-Host "WROTE $Path" -ForegroundColor Green
}

function Assert-CommandSuccess {
    param([Parameter(Mandatory)][string]$Name)

    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

$ExpectedBranch = "feature/m5.3-autonomous-mission-orchestrator"
$CurrentBranch = git branch --show-current
Assert-CommandSuccess "Read current branch"

if ($CurrentBranch -ne $ExpectedBranch) {
    throw "M5.3 Package 3 must run on '$ExpectedBranch'. Current branch: '$CurrentBranch'."
}

Write-Utf8NoBom "forge\autonomous_orchestration\journal.py" @'
"""Append-only orchestration journal."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from forge.autonomous_orchestration.errors import (
    OrchestrationContractError,
)
from forge.autonomous_orchestration.states import OrchestrationState


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class OrchestrationEvent(BaseModel):
    """Immutable orchestration event."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    sequence: int = Field(ge=1)
    event_type: str = Field(min_length=1)
    previous_state: OrchestrationState | None = None
    new_state: OrchestrationState | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


@dataclass(slots=True)
class InMemoryOrchestrationJournal:
    """Deterministic append-only orchestration event store."""

    _events: list[OrchestrationEvent] = field(default_factory=list)

    def append(self, event: OrchestrationEvent) -> None:
        if any(
            existing.event_id == event.event_id
            for existing in self._events
        ):
            raise OrchestrationContractError(
                f"Duplicate orchestration event: {event.event_id}"
            )

        events = self.events_for(event.session_id)
        expected = events[-1].sequence + 1 if events else 1

        if event.sequence != expected:
            raise OrchestrationContractError(
                f"Orchestration event sequence must be {expected}."
            )

        self._events.append(event)

    def events_for(
        self,
        session_id: str,
    ) -> tuple[OrchestrationEvent, ...]:
        return tuple(
            event
            for event in self._events
            if event.session_id == session_id
        )
'@

Write-Utf8NoBom "forge\autonomous_orchestration\outcome_processor.py" @'
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
'@

Write-Utf8NoBom "forge\autonomous_orchestration\recovery.py" @'
"""Bounded orchestration recovery decisions."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_orchestration.models import MissionSession
from forge.autonomous_orchestration.policies import (
    AutonomousOrchestrationPolicy,
)
from forge.autonomous_orchestration.states import OrchestrationState


@dataclass(frozen=True, slots=True)
class RecoveryDecision:
    """Bounded recovery decision for a failed step."""

    target_state: OrchestrationState
    action: str
    allowed: bool
    reason: str


def decide_recovery(
    session: MissionSession,
    policy: AutonomousOrchestrationPolicy,
) -> RecoveryDecision:
    """Select retry, rollback, replan, or escalation deterministically."""
    budgets = policy.budgets

    if session.retry_count < budgets.maximum_retries:
        return RecoveryDecision(
            target_state=OrchestrationState.RETRY_PENDING,
            action="retry",
            allowed=True,
            reason="Retry budget remains.",
        )

    if session.rollback_count < budgets.maximum_rollbacks:
        return RecoveryDecision(
            target_state=OrchestrationState.ROLLBACK_PENDING,
            action="rollback",
            allowed=True,
            reason="Retry budget exhausted; rollback budget remains.",
        )

    if session.replan_count < budgets.maximum_replans:
        return RecoveryDecision(
            target_state=OrchestrationState.REPLAN_PENDING,
            action="replan",
            allowed=True,
            reason="Retry and rollback budgets exhausted; replan remains.",
        )

    return RecoveryDecision(
        target_state=OrchestrationState.ESCALATED,
        action="escalate",
        allowed=False,
        reason="All bounded recovery budgets are exhausted.",
    )
'@

Write-Utf8NoBom "forge\autonomous_orchestration\iteration_service.py" @'
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
'@

Write-Utf8NoBom "forge\autonomous_orchestration\orchestrator.py" @'
"""Top-level bounded autonomous mission orchestrator."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from forge.autonomous_execution.models import ExecutionRequest
from forge.autonomous_execution.runtime import StepExecutionOutcome
from forge.autonomous_orchestration.coordinator import (
    CoordinationResult,
    MissionStepCoordinator,
)
from forge.autonomous_orchestration.iteration_service import (
    OrchestrationIterationService,
)
from forge.autonomous_orchestration.models import (
    MissionSession,
    OrchestrationIteration,
    OrchestrationRequest,
)
from forge.autonomous_runtime.models import AutonomousMission

ExecutionRunner = Callable[[ExecutionRequest], StepExecutionOutcome]


@dataclass(frozen=True, slots=True)
class OrchestrationCycleResult:
    """Result of one bounded orchestration cycle."""

    session: MissionSession
    coordination: CoordinationResult
    iteration: OrchestrationIteration
    execution_performed: bool


@dataclass(slots=True)
class AutonomousMissionOrchestrator:
    """Coordinate and process at most one execution per call."""

    coordinator: MissionStepCoordinator
    iteration_service: OrchestrationIterationService
    execution_runner: ExecutionRunner

    def run_cycle(
        self,
        request: OrchestrationRequest,
        session: MissionSession,
        mission: AutonomousMission,
        execution_request: ExecutionRequest | None = None,
    ) -> OrchestrationCycleResult:
        coordination = self.coordinator.coordinate(
            request,
            session,
            mission,
        )

        if coordination.execution_request_id is None:
            return OrchestrationCycleResult(
                session=coordination.session,
                coordination=coordination,
                iteration=coordination.iteration,
                execution_performed=False,
            )

        if execution_request is None:
            raise ValueError(
                "Execution request is required for selected step."
            )

        outcome = self.execution_runner(execution_request)
        updated, iteration = self.iteration_service.process(
            coordination.session,
            outcome,
            mission_version_before=mission.version,
            execution_request_id=execution_request.request_id,
        )

        return OrchestrationCycleResult(
            session=updated,
            coordination=coordination,
            iteration=iteration,
            execution_performed=True,
        )
'@

Write-Utf8NoBom "tests\test_autonomous_orchestration_journal.py" @'
import pytest

from forge.autonomous_orchestration.errors import (
    OrchestrationContractError,
)
from forge.autonomous_orchestration.journal import (
    InMemoryOrchestrationJournal,
    OrchestrationEvent,
)


def test_journal_enforces_sequence() -> None:
    journal = InMemoryOrchestrationJournal()
    journal.append(
        OrchestrationEvent(
            event_id="event-1",
            session_id="session-1",
            sequence=1,
            event_type="created",
        )
    )

    with pytest.raises(OrchestrationContractError):
        journal.append(
            OrchestrationEvent(
                event_id="event-2",
                session_id="session-1",
                sequence=3,
                event_type="invalid",
            )
        )
'@

Write-Utf8NoBom "tests\test_autonomous_orchestration_outcome_processor.py" @'
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
'@

Write-Utf8NoBom "tests\test_autonomous_orchestration_recovery.py" @'
from forge.autonomous_orchestration.models import MissionSession
from forge.autonomous_orchestration.policies import (
    AutonomousOrchestrationPolicy,
)
from forge.autonomous_orchestration.recovery import decide_recovery
from forge.autonomous_orchestration.states import OrchestrationState


def test_recovery_prefers_retry() -> None:
    decision = decide_recovery(
        MissionSession(
            session_id="session-1",
            mission_id="mission-1",
            plan_id="plan-1",
            plan_version=1,
            repository_root="repository",
        ),
        AutonomousOrchestrationPolicy(),
    )

    assert decision.action == "retry"
    assert decision.target_state is OrchestrationState.RETRY_PENDING
'@

Write-Utf8NoBom "tests\test_autonomous_orchestration_iteration_service.py" @'
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
'@

Write-Host ""
Write-Host "M5.3 Package 3 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check . --fix
Assert-CommandSuccess "Ruff fix"

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_autonomous_orchestration_journal.py `
    .\tests\test_autonomous_orchestration_outcome_processor.py `
    .\tests\test_autonomous_orchestration_recovery.py `
    .\tests\test_autonomous_orchestration_iteration_service.py `
    -p no:cacheprovider
Assert-CommandSuccess "M5.3 Package 3 focused tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M5.3 PACKAGE 3 COMPLETE" -ForegroundColor Green

git status --short