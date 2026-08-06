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

$ExpectedBranch = "feature/m5.1-autonomous-runtime-architecture"
$CurrentBranch = git branch --show-current
Assert-CommandSuccess "Read current branch"

if ($CurrentBranch -ne $ExpectedBranch) {
    throw "M5.1 Package 3 must run on '$ExpectedBranch'. Current branch: '$CurrentBranch'."
}

Write-Utf8NoBom "forge\autonomous_runtime\checkpoints.py" @'
"""Checkpoint contracts and verification helpers."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_runtime.errors import MissionContractError
from forge.autonomous_runtime.models import MissionCheckpoint


@dataclass(frozen=True, slots=True)
class CheckpointVerification:
    """Result of checkpoint verification."""

    valid: bool
    reason: str


def verify_checkpoint(
    checkpoint: MissionCheckpoint,
    *,
    expected_mission_id: str,
    expected_step_id: str | None = None,
    expected_repository_fingerprint: str | None = None,
) -> CheckpointVerification:
    """Verify checkpoint identity, ownership, and fingerprint."""
    if checkpoint.mission_id != expected_mission_id:
        return CheckpointVerification(
            valid=False,
            reason="Checkpoint belongs to another mission.",
        )

    if (
        expected_step_id is not None
        and checkpoint.step_id != expected_step_id
    ):
        return CheckpointVerification(
            valid=False,
            reason="Checkpoint belongs to another step.",
        )

    if not checkpoint.verified:
        return CheckpointVerification(
            valid=False,
            reason="Checkpoint has not been verified.",
        )

    if (
        expected_repository_fingerprint is not None
        and checkpoint.repository_fingerprint
        != expected_repository_fingerprint
    ):
        return CheckpointVerification(
            valid=False,
            reason="Checkpoint repository fingerprint does not match.",
        )

    if not checkpoint.working_tree_digest:
        return CheckpointVerification(
            valid=False,
            reason="Checkpoint working-tree digest is missing.",
        )

    return CheckpointVerification(
        valid=True,
        reason="Checkpoint is valid.",
    )


def assert_checkpoint_valid(
    checkpoint: MissionCheckpoint,
    *,
    expected_mission_id: str,
    expected_step_id: str | None = None,
    expected_repository_fingerprint: str | None = None,
) -> None:
    """Raise when a checkpoint cannot be used for recovery."""
    result = verify_checkpoint(
        checkpoint,
        expected_mission_id=expected_mission_id,
        expected_step_id=expected_step_id,
        expected_repository_fingerprint=(
            expected_repository_fingerprint
        ),
    )

    if not result.valid:
        raise MissionContractError(result.reason)
'@

Write-Utf8NoBom "forge\autonomous_runtime\recovery.py" @'
"""Bounded recovery decision engine."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_runtime.errors import MissionContractError
from forge.autonomous_runtime.models import (
    AutonomousMission,
    MissionCheckpoint,
)
from forge.autonomous_runtime.states import RecoveryAction


@dataclass(frozen=True, slots=True)
class RecoveryContext:
    """Inputs required to choose a recovery action."""

    failure_class: str
    step_attempt_number: int
    rollback_attempt_number: int
    retryable: bool
    checkpoint: MissionCheckpoint | None = None
    mission_can_replan: bool = True


@dataclass(frozen=True, slots=True)
class RecoveryEvaluation:
    """Deterministic recovery decision."""

    action: RecoveryAction
    reason: str


_FATAL_FAILURES = frozenset(
    {
        "invariant_violation",
        "rollback_failure",
        "checkpoint_corruption",
        "authority_failure",
        "approval_failure",
    }
)


def choose_recovery_action(
    mission: AutonomousMission,
    context: RecoveryContext,
) -> RecoveryEvaluation:
    """Choose a bounded recovery action from mission policy."""
    budgets = mission.request.budgets

    if context.failure_class in _FATAL_FAILURES:
        return RecoveryEvaluation(
            action=RecoveryAction.ESCALATE,
            reason="Failure class requires human escalation.",
        )

    if context.retryable and (
        context.step_attempt_number
        < budgets.maximum_attempts_per_step
    ):
        return RecoveryEvaluation(
            action=RecoveryAction.RETRY_STEP,
            reason="Retryable failure and step budget remains.",
        )

    if context.checkpoint is not None and (
        context.rollback_attempt_number
        < budgets.maximum_rollback_attempts
    ):
        return RecoveryEvaluation(
            action=RecoveryAction.ROLLBACK_STEP,
            reason="Verified rollback path should be attempted.",
        )

    if (
        context.mission_can_replan
        and mission.replan_count < budgets.maximum_replans
    ):
        return RecoveryEvaluation(
            action=RecoveryAction.REPLAN,
            reason="Retry exhausted; replan budget remains.",
        )

    return RecoveryEvaluation(
        action=RecoveryAction.ABORT,
        reason="No safe recovery budget remains.",
    )


def assert_recovery_action_allowed(
    mission: AutonomousMission,
    context: RecoveryContext,
    requested: RecoveryAction,
) -> None:
    """Raise when a requested recovery action violates policy."""
    evaluated = choose_recovery_action(mission, context)

    if evaluated.action is not requested:
        raise MissionContractError(
            "Requested recovery action is not permitted: "
            f"expected {evaluated.action.value}, got {requested.value}."
        )
'@

Write-Utf8NoBom "forge\autonomous_runtime\events.py" @'
"""Append-only mission event journal contracts."""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.autonomous_runtime.errors import MissionContractError
from forge.autonomous_runtime.models import MissionEvent


@dataclass(slots=True)
class InMemoryMissionEventJournal:
    """Deterministic append-only event journal for M5.1."""

    _events: list[MissionEvent] = field(default_factory=list)

    def append(self, event: MissionEvent) -> None:
        """Append one event while enforcing ordering and uniqueness."""
        if any(
            existing.event_id == event.event_id
            for existing in self._events
        ):
            raise MissionContractError(
                f"Duplicate mission event identifier: {event.event_id}"
            )

        mission_events = [
            existing
            for existing in self._events
            if existing.mission_id == event.mission_id
        ]

        expected_sequence = (
            mission_events[-1].sequence + 1
            if mission_events
            else 1
        )

        if event.sequence != expected_sequence:
            raise MissionContractError(
                "Mission event sequence is invalid: "
                f"expected {expected_sequence}, got {event.sequence}."
            )

        self._events.append(event)

    def events_for(
        self,
        mission_id: str,
    ) -> tuple[MissionEvent, ...]:
        """Return immutable ordered events for one mission."""
        return tuple(
            event
            for event in self._events
            if event.mission_id == mission_id
        )

    def latest_for(
        self,
        mission_id: str,
    ) -> MissionEvent | None:
        """Return the latest event for one mission."""
        events = self.events_for(mission_id)
        return events[-1] if events else None
'@

Write-Utf8NoBom "forge\autonomous_runtime\recovery_service.py" @'
"""Application service for checkpoint and recovery control."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_runtime.checkpoints import (
    assert_checkpoint_valid,
)
from forge.autonomous_runtime.models import (
    AutonomousMission,
    MissionCheckpoint,
)
from forge.autonomous_runtime.recovery import (
    RecoveryContext,
    RecoveryEvaluation,
    choose_recovery_action,
)


@dataclass(frozen=True, slots=True)
class RecoveryRequest:
    """Recovery request for one failed mission step."""

    failure_class: str
    step_attempt_number: int
    rollback_attempt_number: int
    retryable: bool
    checkpoint: MissionCheckpoint | None = None
    mission_can_replan: bool = True
    expected_step_id: str | None = None
    expected_repository_fingerprint: str | None = None


class AutonomousRecoveryService:
    """Coordinate checkpoint validation and recovery selection."""

    def evaluate(
        self,
        mission: AutonomousMission,
        request: RecoveryRequest,
    ) -> RecoveryEvaluation:
        if request.checkpoint is not None:
            assert_checkpoint_valid(
                request.checkpoint,
                expected_mission_id=mission.mission_id,
                expected_step_id=request.expected_step_id,
                expected_repository_fingerprint=(
                    request.expected_repository_fingerprint
                ),
            )

        return choose_recovery_action(
            mission,
            RecoveryContext(
                failure_class=request.failure_class,
                step_attempt_number=(
                    request.step_attempt_number
                ),
                rollback_attempt_number=(
                    request.rollback_attempt_number
                ),
                retryable=request.retryable,
                checkpoint=request.checkpoint,
                mission_can_replan=request.mission_can_replan,
            ),
        )
'@

Write-Utf8NoBom "tests\test_autonomous_runtime_checkpoints.py" @'
import pytest

from forge.autonomous_runtime.checkpoints import (
    assert_checkpoint_valid,
    verify_checkpoint,
)
from forge.autonomous_runtime.errors import MissionContractError
from forge.autonomous_runtime.models import MissionCheckpoint


def checkpoint(
    *,
    verified: bool = True,
) -> MissionCheckpoint:
    return MissionCheckpoint(
        checkpoint_id="checkpoint-1",
        mission_id="mission-1",
        step_id="step-1",
        kind="git_stash",
        repository_fingerprint="fingerprint-1",
        working_tree_digest="tree-1",
        verified=verified,
    )


def test_verified_checkpoint_passes() -> None:
    result = verify_checkpoint(
        checkpoint(),
        expected_mission_id="mission-1",
        expected_step_id="step-1",
        expected_repository_fingerprint="fingerprint-1",
    )

    assert result.valid


def test_unverified_checkpoint_is_rejected() -> None:
    with pytest.raises(MissionContractError):
        assert_checkpoint_valid(
            checkpoint(verified=False),
            expected_mission_id="mission-1",
        )
'@

Write-Utf8NoBom "tests\test_autonomous_runtime_recovery_engine.py" @'
from forge.autonomous_runtime.models import (
    AutonomousMission,
    MissionCheckpoint,
    MissionRequest,
)
from forge.autonomous_runtime.recovery import (
    RecoveryContext,
    choose_recovery_action,
)
from forge.autonomous_runtime.states import (
    AuthorityLevel,
    RecoveryAction,
)


def mission() -> AutonomousMission:
    return AutonomousMission(
        mission_id="mission-1",
        request=MissionRequest(
            request_id="request-1",
            objective="Recover safely.",
            repository_root="repository",
            requested_authority=AuthorityLevel.A2_MODIFY,
            requested_by="Aerion",
        ),
        granted_authority=AuthorityLevel.A2_MODIFY,
    )


def checkpoint() -> MissionCheckpoint:
    return MissionCheckpoint(
        checkpoint_id="checkpoint-1",
        mission_id="mission-1",
        step_id="step-1",
        kind="git_stash",
        repository_fingerprint="fingerprint-1",
        working_tree_digest="tree-1",
        verified=True,
    )


def test_retryable_failure_uses_retry_budget_first() -> None:
    result = choose_recovery_action(
        mission(),
        RecoveryContext(
            failure_class="transient_tool_failure",
            step_attempt_number=1,
            rollback_attempt_number=0,
            retryable=True,
            checkpoint=checkpoint(),
        ),
    )

    assert result.action is RecoveryAction.RETRY_STEP


def test_fatal_failure_escalates() -> None:
    result = choose_recovery_action(
        mission(),
        RecoveryContext(
            failure_class="rollback_failure",
            step_attempt_number=2,
            rollback_attempt_number=1,
            retryable=False,
        ),
    )

    assert result.action is RecoveryAction.ESCALATE
'@

Write-Utf8NoBom "tests\test_autonomous_runtime_events.py" @'
import pytest

from forge.autonomous_runtime.errors import MissionContractError
from forge.autonomous_runtime.events import (
    InMemoryMissionEventJournal,
)
from forge.autonomous_runtime.models import MissionEvent
from forge.autonomous_runtime.states import MissionState


def event(
    event_id: str,
    sequence: int,
) -> MissionEvent:
    return MissionEvent(
        event_id=event_id,
        mission_id="mission-1",
        sequence=sequence,
        event_type="mission_state_changed",
        previous_state=(
            MissionState.RECEIVED
            if sequence == 1
            else MissionState.QUALIFYING
        ),
        new_state=(
            MissionState.QUALIFYING
            if sequence == 1
            else MissionState.QUALIFIED
        ),
        actor="runtime",
    )


def test_event_journal_is_ordered_and_append_only() -> None:
    journal = InMemoryMissionEventJournal()
    journal.append(event("event-1", 1))
    journal.append(event("event-2", 2))

    assert [item.sequence for item in journal.events_for("mission-1")] == [
        1,
        2,
    ]


def test_invalid_event_sequence_is_rejected() -> None:
    journal = InMemoryMissionEventJournal()

    with pytest.raises(MissionContractError):
        journal.append(event("event-2", 2))
'@

Write-Utf8NoBom "tests\test_autonomous_runtime_recovery_service.py" @'
from forge.autonomous_runtime.models import (
    AutonomousMission,
    MissionCheckpoint,
    MissionRequest,
)
from forge.autonomous_runtime.recovery_service import (
    AutonomousRecoveryService,
    RecoveryRequest,
)
from forge.autonomous_runtime.states import (
    AuthorityLevel,
    RecoveryAction,
)


def mission() -> AutonomousMission:
    return AutonomousMission(
        mission_id="mission-1",
        request=MissionRequest(
            request_id="request-1",
            objective="Recover safely.",
            repository_root="repository",
            requested_authority=AuthorityLevel.A2_MODIFY,
            requested_by="Aerion",
        ),
        granted_authority=AuthorityLevel.A2_MODIFY,
    )


def test_service_validates_checkpoint_and_selects_rollback() -> None:
    checkpoint = MissionCheckpoint(
        checkpoint_id="checkpoint-1",
        mission_id="mission-1",
        step_id="step-1",
        kind="git_stash",
        repository_fingerprint="fingerprint-1",
        working_tree_digest="tree-1",
        verified=True,
    )

    result = AutonomousRecoveryService().evaluate(
        mission(),
        RecoveryRequest(
            failure_class="validation_failure",
            step_attempt_number=2,
            rollback_attempt_number=0,
            retryable=False,
            checkpoint=checkpoint,
            expected_step_id="step-1",
            expected_repository_fingerprint="fingerprint-1",
        ),
    )

    assert result.action is RecoveryAction.ROLLBACK_STEP
'@

Write-Host ""
Write-Host "M5.1 Package 3 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check . --fix
Assert-CommandSuccess "Ruff fix"

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_autonomous_runtime_checkpoints.py `
    .\tests\test_autonomous_runtime_recovery_engine.py `
    .\tests\test_autonomous_runtime_events.py `
    .\tests\test_autonomous_runtime_recovery_service.py `
    -p no:cacheprovider
Assert-CommandSuccess "M5.1 Package 3 focused tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M5.1 PACKAGE 3 COMPLETE" -ForegroundColor Green

git status --short
