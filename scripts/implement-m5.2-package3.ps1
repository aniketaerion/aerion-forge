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
    New-Item -ItemType Directory -Path $Directory -Force | Out-Null

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

$ExpectedBranch = "feature/m5.2-autonomous-execution-engine"
$CurrentBranch = git branch --show-current
Assert-CommandSuccess "Read current branch"

if ($CurrentBranch -ne $ExpectedBranch) {
    throw "M5.2 Package 3 must run on '$ExpectedBranch'. Current branch: '$CurrentBranch'."
}

Write-Utf8NoBom "forge\autonomous_execution\execution_transitions.py" @'
"""State transitions for one autonomous step execution."""

from __future__ import annotations

from types import MappingProxyType
from typing import Final, Mapping

from forge.autonomous_execution.errors import ExecutionContractError
from forge.autonomous_execution.states import (
    StepExecutionState,
    TERMINAL_EXECUTION_STATES,
)


_TRANSITIONS: dict[
    StepExecutionState,
    frozenset[StepExecutionState],
] = {
    StepExecutionState.PENDING: frozenset(
        {
            StepExecutionState.ELIGIBILITY_CHECK,
            StepExecutionState.CANCELLED,
        }
    ),
    StepExecutionState.ELIGIBILITY_CHECK: frozenset(
        {
            StepExecutionState.READY,
            StepExecutionState.BLOCKED,
            StepExecutionState.AWAITING_APPROVAL,
            StepExecutionState.FAILED,
            StepExecutionState.CANCELLED,
        }
    ),
    StepExecutionState.READY: frozenset(
        {
            StepExecutionState.LEASE_ACQUIRING,
            StepExecutionState.PAUSED,
            StepExecutionState.CANCELLED,
        }
    ),
    StepExecutionState.LEASE_ACQUIRING: frozenset(
        {
            StepExecutionState.CHECKPOINT_VERIFYING,
            StepExecutionState.BLOCKED,
            StepExecutionState.FAILED,
        }
    ),
    StepExecutionState.CHECKPOINT_VERIFYING: frozenset(
        {
            StepExecutionState.TOOL_PREPARING,
            StepExecutionState.BLOCKED,
            StepExecutionState.FAILED,
        }
    ),
    StepExecutionState.TOOL_PREPARING: frozenset(
        {
            StepExecutionState.TOOL_RUNNING,
            StepExecutionState.AWAITING_APPROVAL,
            StepExecutionState.BLOCKED,
            StepExecutionState.FAILED,
        }
    ),
    StepExecutionState.TOOL_RUNNING: frozenset(
        {
            StepExecutionState.EFFECT_VERIFYING,
            StepExecutionState.RETRY_PENDING,
            StepExecutionState.ROLLBACK_PENDING,
            StepExecutionState.FAILED,
            StepExecutionState.CANCELLED,
        }
    ),
    StepExecutionState.EFFECT_VERIFYING: frozenset(
        {
            StepExecutionState.EVIDENCE_RECORDING,
            StepExecutionState.ROLLBACK_PENDING,
            StepExecutionState.ESCALATED,
            StepExecutionState.FAILED,
        }
    ),
    StepExecutionState.EVIDENCE_RECORDING: frozenset(
        {
            StepExecutionState.SUCCEEDED,
            StepExecutionState.FAILED,
        }
    ),
    StepExecutionState.RETRY_PENDING: frozenset(
        {
            StepExecutionState.TOOL_PREPARING,
            StepExecutionState.ROLLBACK_PENDING,
            StepExecutionState.ESCALATED,
            StepExecutionState.FAILED,
        }
    ),
    StepExecutionState.ROLLBACK_PENDING: frozenset(
        {
            StepExecutionState.ROLLED_BACK,
            StepExecutionState.ESCALATED,
            StepExecutionState.FAILED,
        }
    ),
    StepExecutionState.ROLLED_BACK: frozenset(
        {
            StepExecutionState.RETRY_PENDING,
            StepExecutionState.PAUSED,
            StepExecutionState.ESCALATED,
            StepExecutionState.FAILED,
        }
    ),
    StepExecutionState.BLOCKED: frozenset(
        {
            StepExecutionState.ELIGIBILITY_CHECK,
            StepExecutionState.PAUSED,
            StepExecutionState.ESCALATED,
            StepExecutionState.CANCELLED,
            StepExecutionState.FAILED,
        }
    ),
    StepExecutionState.AWAITING_APPROVAL: frozenset(
        {
            StepExecutionState.TOOL_PREPARING,
            StepExecutionState.PAUSED,
            StepExecutionState.CANCELLED,
            StepExecutionState.FAILED,
        }
    ),
    StepExecutionState.PAUSED: frozenset(
        {
            StepExecutionState.ELIGIBILITY_CHECK,
            StepExecutionState.CANCELLED,
            StepExecutionState.FAILED,
        }
    ),
    StepExecutionState.ESCALATED: frozenset(
        {
            StepExecutionState.PAUSED,
            StepExecutionState.CANCELLED,
            StepExecutionState.FAILED,
        }
    ),
    StepExecutionState.SUCCEEDED: frozenset(),
    StepExecutionState.FAILED: frozenset(),
    StepExecutionState.CANCELLED: frozenset(),
}

EXECUTION_TRANSITIONS: Final[
    Mapping[
        StepExecutionState,
        frozenset[StepExecutionState],
    ]
] = MappingProxyType(_TRANSITIONS)


def assert_execution_transition(
    current: StepExecutionState,
    target: StepExecutionState,
) -> None:
    """Raise when an execution transition is illegal."""
    if current in TERMINAL_EXECUTION_STATES:
        raise ExecutionContractError(
            f"Terminal execution cannot transition from {current.value}."
        )

    if target not in EXECUTION_TRANSITIONS[current]:
        raise ExecutionContractError(
            f"Illegal execution transition: "
            f"{current.value} -> {target.value}"
        )
'@

Write-Utf8NoBom "forge\autonomous_execution\execution_journal.py" @'
"""Append-only journal for step execution events."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from forge.autonomous_execution.errors import ExecutionContractError
from forge.autonomous_execution.states import StepExecutionState


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ExecutionEvent(BaseModel):
    """Immutable step execution event."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: str = Field(min_length=1)
    execution_id: str = Field(min_length=1)
    sequence: int = Field(ge=1)
    event_type: str = Field(min_length=1)
    previous_state: StepExecutionState | None = None
    new_state: StepExecutionState | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


@dataclass(slots=True)
class InMemoryExecutionJournal:
    """Deterministic append-only execution journal."""

    _events: list[ExecutionEvent] = field(default_factory=list)

    def append(self, event: ExecutionEvent) -> None:
        if any(
            existing.event_id == event.event_id
            for existing in self._events
        ):
            raise ExecutionContractError(
                f"Duplicate execution event: {event.event_id}"
            )

        events = self.events_for(event.execution_id)
        expected = events[-1].sequence + 1 if events else 1

        if event.sequence != expected:
            raise ExecutionContractError(
                f"Execution event sequence must be {expected}."
            )

        self._events.append(event)

    def events_for(
        self,
        execution_id: str,
    ) -> tuple[ExecutionEvent, ...]:
        return tuple(
            event
            for event in self._events
            if event.execution_id == execution_id
        )
'@

Write-Utf8NoBom "forge\autonomous_execution\lease_manager.py" @'
"""Single-writer execution lease management."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from forge.autonomous_execution.errors import ExecutionContractError
from forge.autonomous_execution.identifiers import (
    execution_lease_identifier,
)
from forge.autonomous_execution.models import ExecutionLease


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class InMemoryExecutionLeaseManager:
    """Single-writer repository lease manager."""

    _leases: dict[str, ExecutionLease] = field(default_factory=dict)

    def acquire(
        self,
        *,
        mission_id: str,
        repository_root: str,
        holder: str,
        lease_seconds: int,
        now: datetime | None = None,
    ) -> ExecutionLease:
        moment = now or utc_now()
        active = self._leases.get(repository_root)

        if (
            active is not None
            and active.released_at is None
            and active.expires_at > moment
        ):
            raise ExecutionContractError(
                "Repository already has an active execution lease."
            )

        payload = {
            "mission_id": mission_id,
            "repository_root": repository_root,
            "holder": holder,
            "acquired_at": moment.isoformat(),
        }
        lease = ExecutionLease(
            lease_id=execution_lease_identifier(payload),
            mission_id=mission_id,
            repository_root=repository_root,
            holder=holder,
            acquired_at=moment,
            expires_at=moment + timedelta(seconds=lease_seconds),
        )
        self._leases[repository_root] = lease
        return lease

    def release(
        self,
        lease: ExecutionLease,
        *,
        now: datetime | None = None,
    ) -> ExecutionLease:
        moment = now or utc_now()
        current = self._leases.get(lease.repository_root)

        if current is None or current.lease_id != lease.lease_id:
            raise ExecutionContractError(
                "Execution lease is not active."
            )

        released = lease.model_copy(
            update={
                "released_at": moment,
                "version": lease.version + 1,
            }
        )
        self._leases[lease.repository_root] = released
        return released
'@

Write-Utf8NoBom "forge\autonomous_execution\evidence.py" @'
"""Execution evidence creation."""

from __future__ import annotations

from forge.autonomous_execution.identifiers import (
    execution_evidence_identifier,
)
from forge.autonomous_execution.models import ExecutionEvidence
from forge.autonomous_execution.tool_contracts import ToolExecutionResult


def build_execution_evidence(
    *,
    execution_id: str,
    result: ToolExecutionResult,
    repository_fingerprint: str,
) -> ExecutionEvidence:
    """Create deterministic evidence from a tool result."""
    payload = {
        "execution_id": execution_id,
        "invocation_id": result.invocation_id,
        "status": result.status.value,
        "result_digest": result.result_digest,
        "repository_fingerprint": repository_fingerprint,
    }

    return ExecutionEvidence(
        evidence_id=execution_evidence_identifier(payload),
        execution_id=execution_id,
        invocation_id=result.invocation_id,
        evidence_kind="tool_execution",
        summary=f"Tool execution ended with {result.status.value}.",
        artifact_references=tuple(
            item
            for item in (
                result.stdout_reference,
                result.stderr_reference,
            )
            if item is not None
        ),
        repository_fingerprint=repository_fingerprint,
    )
'@

Write-Utf8NoBom "forge\autonomous_execution\runtime.py" @'
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
'@

Write-Utf8NoBom "tests\test_autonomous_execution_transitions.py" @'
import pytest

from forge.autonomous_execution.errors import ExecutionContractError
from forge.autonomous_execution.execution_transitions import (
    assert_execution_transition,
)
from forge.autonomous_execution.states import StepExecutionState


def test_legal_execution_transition_passes() -> None:
    assert_execution_transition(
        StepExecutionState.PENDING,
        StepExecutionState.ELIGIBILITY_CHECK,
    )


def test_illegal_execution_transition_is_rejected() -> None:
    with pytest.raises(ExecutionContractError):
        assert_execution_transition(
            StepExecutionState.PENDING,
            StepExecutionState.TOOL_RUNNING,
        )


def test_terminal_execution_cannot_resume() -> None:
    with pytest.raises(ExecutionContractError):
        assert_execution_transition(
            StepExecutionState.SUCCEEDED,
            StepExecutionState.READY,
        )
'@

Write-Utf8NoBom "tests\test_autonomous_execution_lease_manager.py" @'
from datetime import datetime, timezone

import pytest

from forge.autonomous_execution.errors import ExecutionContractError
from forge.autonomous_execution.lease_manager import (
    InMemoryExecutionLeaseManager,
)


def test_single_writer_lease_is_enforced() -> None:
    manager = InMemoryExecutionLeaseManager()
    now = datetime.now(timezone.utc)

    manager.acquire(
        mission_id="mission-1",
        repository_root="repository",
        holder="runtime-1",
        lease_seconds=60,
        now=now,
    )

    with pytest.raises(ExecutionContractError):
        manager.acquire(
            mission_id="mission-2",
            repository_root="repository",
            holder="runtime-2",
            lease_seconds=60,
            now=now,
        )


def test_released_lease_allows_new_writer() -> None:
    manager = InMemoryExecutionLeaseManager()
    now = datetime.now(timezone.utc)

    lease = manager.acquire(
        mission_id="mission-1",
        repository_root="repository",
        holder="runtime-1",
        lease_seconds=60,
        now=now,
    )
    manager.release(lease, now=now)

    next_lease = manager.acquire(
        mission_id="mission-2",
        repository_root="repository",
        holder="runtime-2",
        lease_seconds=60,
        now=now,
    )

    assert next_lease.mission_id == "mission-2"
'@

Write-Utf8NoBom "tests\test_autonomous_execution_evidence.py" @'
from forge.autonomous_execution.evidence import (
    build_execution_evidence,
)
from forge.autonomous_execution.states import ToolExecutionStatus
from forge.autonomous_execution.tool_contracts import ToolExecutionResult


def test_evidence_is_built_from_tool_result() -> None:
    result = ToolExecutionResult(
        invocation_id="invocation-1",
        status=ToolExecutionStatus.SUCCEEDED,
        exit_code=0,
        result_digest="digest-1",
        started_at="2026-08-06T00:00:00+00:00",
        completed_at="2026-08-06T00:00:01+00:00",
    )

    evidence = build_execution_evidence(
        execution_id="execution-1",
        result=result,
        repository_fingerprint="fingerprint-1",
    )

    assert evidence.invocation_id == "invocation-1"
    assert evidence.repository_fingerprint == "fingerprint-1"
'@

Write-Utf8NoBom "tests\test_autonomous_execution_runtime.py" @'
from forge.autonomous_execution.execution_journal import (
    InMemoryExecutionJournal,
)
from forge.autonomous_execution.lease_manager import (
    InMemoryExecutionLeaseManager,
)
from forge.autonomous_execution.models import ExecutionRequest
from forge.autonomous_execution.policies import (
    AutonomousExecutionPolicy,
)
from forge.autonomous_execution.runtime import (
    AutonomousExecutionRuntime,
)
from forge.autonomous_execution.states import (
    StepExecutionState,
)
from forge.autonomous_execution.tool_contracts import (
    ToolDefinition,
    ToolExecutionRequest,
)
from forge.autonomous_execution.tool_execution import ToolExecutor
from forge.autonomous_execution.tool_gateway import (
    ControlledToolGateway,
)
from forge.autonomous_execution.tool_registry import ToolRegistry
from forge.autonomous_runtime.states import AuthorityLevel, RiskClass


def runtime() -> AutonomousExecutionRuntime:
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            tool_name="ruff",
            action_kinds=("check",),
            authority_required=AuthorityLevel.A0_READ,
            risk_class=RiskClass.R0_READ_ONLY,
            argument_schema={"path": "str"},
        )
    )

    executor = ToolExecutor()
    executor.register_handler(
        "ruff",
        lambda request: (0, (), "digest-1"),
    )

    policy = AutonomousExecutionPolicy()
    return AutonomousExecutionRuntime(
        gateway=ControlledToolGateway(
            registry=registry,
            executor=executor,
            policy=policy,
        ),
        leases=InMemoryExecutionLeaseManager(),
        journal=InMemoryExecutionJournal(),
        policy=policy,
    )


def test_runtime_executes_one_step_successfully() -> None:
    result = runtime().execute(
        ExecutionRequest(
            request_id="request-1",
            mission_id="mission-1",
            plan_id="plan-1",
            step_id="step-1",
            repository_root="repository",
            requested_by="Aerion",
        ),
        ToolExecutionRequest(
            invocation_id="invocation-1",
            mission_id="mission-1",
            step_id="step-1",
            tool_name="ruff",
            action_kind="check",
            arguments={"path": "."},
            dry_run=True,
        ),
        repository_fingerprint="fingerprint-1",
    )

    assert result.record.state is StepExecutionState.SUCCEEDED
    assert len(result.evidence) == 1
    assert result.record.evidence_ids
'@

Write-Host ""
Write-Host "M5.2 Package 3 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check . --fix
Assert-CommandSuccess "Ruff fix"

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_autonomous_execution_transitions.py `
    .\tests\test_autonomous_execution_lease_manager.py `
    .\tests\test_autonomous_execution_evidence.py `
    .\tests\test_autonomous_execution_runtime.py `
    -p no:cacheprovider
Assert-CommandSuccess "M5.2 Package 3 focused tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M5.2 PACKAGE 3 COMPLETE" -ForegroundColor Green

git status --short