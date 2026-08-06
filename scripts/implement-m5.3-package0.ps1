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
    throw "M5.3 Package 0 must run on '$ExpectedBranch'. Current branch: '$CurrentBranch'."
}

Write-Utf8NoBom "forge\autonomous_orchestration\errors.py" @'
"""Typed errors for autonomous mission orchestration."""

from __future__ import annotations


class AutonomousOrchestrationError(RuntimeError):
    """Base error for orchestration failures."""


class OrchestrationContractError(AutonomousOrchestrationError):
    """Raised when an orchestration contract is invalid."""


class OrchestrationIdentifierError(AutonomousOrchestrationError):
    """Raised when an orchestration identifier cannot be created."""


class OrchestrationPolicyError(AutonomousOrchestrationError):
    """Raised when orchestration policy is unsafe or inconsistent."""


class OrchestrationStateError(AutonomousOrchestrationError):
    """Raised when an orchestration state transition is invalid."""


class OrchestrationResumeError(AutonomousOrchestrationError):
    """Raised when an orchestration session cannot resume."""
'@

Write-Utf8NoBom "forge\autonomous_orchestration\states.py" @'
"""State and outcome enumerations for mission orchestration."""

from __future__ import annotations

from enum import StrEnum


class OrchestrationState(StrEnum):
    """Authoritative orchestration-session states."""

    CREATED = "created"
    INITIALIZING = "initializing"
    PLAN_LOADING = "plan_loading"
    READY = "ready"
    STEP_SELECTING = "step_selecting"
    STEP_PREPARING = "step_preparing"
    STEP_EXECUTING = "step_executing"
    OUTCOME_PROCESSING = "outcome_processing"
    PROGRESS_UPDATING = "progress_updating"
    CONTINUE_CHECK = "continue_check"
    AWAITING_APPROVAL = "awaiting_approval"
    RETRY_PENDING = "retry_pending"
    ROLLBACK_PENDING = "rollback_pending"
    REPLAN_PENDING = "replan_pending"
    PAUSED = "paused"
    RESUME_VALIDATING = "resume_validating"
    ESCALATED = "escalated"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class OrchestrationStopKind(StrEnum):
    """Explicit orchestration stop categories."""

    AWAITING_APPROVAL = "awaiting_approval"
    BLOCKED = "blocked"
    PAUSED = "paused"
    ESCALATED = "escalated"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class IterationOutcome(StrEnum):
    """Outcome of one bounded orchestration iteration."""

    STEP_SELECTED = "step_selected"
    STEP_SUCCEEDED = "step_succeeded"
    STEP_FAILED = "step_failed"
    DRY_RUN_COMPLETED = "dry_run_completed"
    RETRY_REQUIRED = "retry_required"
    ROLLBACK_REQUIRED = "rollback_required"
    REPLAN_REQUIRED = "replan_required"
    APPROVAL_REQUIRED = "approval_required"
    PAUSED = "paused"
    ESCALATED = "escalated"
    MISSION_COMPLETED = "mission_completed"
    NO_ELIGIBLE_STEP = "no_eligible_step"


TERMINAL_ORCHESTRATION_STATES: frozenset[OrchestrationState] = frozenset(
    {
        OrchestrationState.COMPLETED,
        OrchestrationState.FAILED,
        OrchestrationState.CANCELLED,
    }
)


RESUMABLE_ORCHESTRATION_STATES: frozenset[OrchestrationState] = frozenset(
    {
        OrchestrationState.PAUSED,
        OrchestrationState.AWAITING_APPROVAL,
        OrchestrationState.RETRY_PENDING,
        OrchestrationState.ROLLBACK_PENDING,
        OrchestrationState.REPLAN_PENDING,
        OrchestrationState.ESCALATED,
    }
)
'@

Write-Utf8NoBom "forge\autonomous_orchestration\identifiers.py" @'
"""Deterministic identifiers for orchestration records."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from forge.autonomous_orchestration.errors import (
    OrchestrationIdentifierError,
)
from forge.autonomous_runtime.identifiers import deterministic_identifier


def _identifier(
    prefix: str,
    payload: Mapping[str, Any],
) -> str:
    try:
        return deterministic_identifier(prefix, payload)
    except Exception as exc:  # pragma: no cover - defensive boundary
        raise OrchestrationIdentifierError(
            f"Unable to create {prefix} identifier."
        ) from exc


def orchestration_request_identifier(
    payload: Mapping[str, Any],
) -> str:
    return _identifier("orchestration-request", payload)


def mission_session_identifier(
    payload: Mapping[str, Any],
) -> str:
    return _identifier("mission-session", payload)


def orchestration_iteration_identifier(
    payload: Mapping[str, Any],
) -> str:
    return _identifier("orchestration-iteration", payload)


def session_checkpoint_identifier(
    payload: Mapping[str, Any],
) -> str:
    return _identifier("session-checkpoint", payload)


def orchestration_stop_identifier(
    payload: Mapping[str, Any],
) -> str:
    return _identifier("orchestration-stop", payload)
'@

Write-Utf8NoBom "forge\autonomous_orchestration\policies.py" @'
"""Bounded orchestration policies."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from forge.autonomous_orchestration.errors import (
    OrchestrationPolicyError,
)


class OrchestrationBudgetPolicy(BaseModel):
    """Finite mission-orchestration budgets."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    maximum_cycles: int = Field(default=25, ge=1, le=500)
    maximum_step_executions: int = Field(default=20, ge=1, le=500)
    maximum_retries: int = Field(default=3, ge=0, le=50)
    maximum_rollbacks: int = Field(default=2, ge=0, le=20)
    maximum_replans: int = Field(default=2, ge=0, le=20)
    maximum_resume_attempts: int = Field(default=3, ge=0, le=20)

    @model_validator(mode="after")
    def validate_budget_relationships(
        self,
    ) -> OrchestrationBudgetPolicy:
        if self.maximum_cycles < self.maximum_step_executions:
            raise ValueError(
                "maximum_cycles must cover maximum_step_executions."
            )

        recovery_budget = (
            self.maximum_retries
            + self.maximum_rollbacks
            + self.maximum_replans
        )
        if recovery_budget > self.maximum_cycles:
            raise ValueError(
                "Combined recovery budgets cannot exceed "
                "maximum_cycles."
            )

        return self


class OrchestrationSafetyPolicy(BaseModel):
    """Default-safe orchestration behaviour."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    dry_run_by_default: bool = True
    one_active_session_per_mission: bool = True
    one_execution_per_iteration: bool = True
    require_approved_plan: bool = True
    require_plan_version_match: bool = True
    require_verified_resume_checkpoint: bool = True
    require_optimistic_versioning: bool = True
    stop_on_approval_boundary: bool = True
    stop_on_scope_violation: bool = True
    stop_on_invariant_violation: bool = True
    allow_terminal_resume: bool = False
    allow_completed_step_replay: bool = False

    @model_validator(mode="after")
    def validate_safety_invariants(
        self,
    ) -> OrchestrationSafetyPolicy:
        violations: list[str] = []

        if not self.one_active_session_per_mission:
            violations.append(
                "one active session per mission is mandatory"
            )
        if not self.one_execution_per_iteration:
            violations.append(
                "one execution per iteration is mandatory"
            )
        if not self.require_approved_plan:
            violations.append("approved plan is mandatory")
        if not self.require_plan_version_match:
            violations.append("plan-version matching is mandatory")
        if not self.require_verified_resume_checkpoint:
            violations.append(
                "verified resume checkpoint is mandatory"
            )
        if not self.require_optimistic_versioning:
            violations.append(
                "optimistic versioning is mandatory"
            )
        if not self.stop_on_approval_boundary:
            violations.append(
                "approval boundaries must stop orchestration"
            )
        if not self.stop_on_scope_violation:
            violations.append(
                "scope violations must stop orchestration"
            )
        if not self.stop_on_invariant_violation:
            violations.append(
                "invariant violations must stop orchestration"
            )
        if self.allow_terminal_resume:
            violations.append(
                "terminal sessions cannot resume"
            )
        if self.allow_completed_step_replay:
            violations.append(
                "completed steps cannot be replayed"
            )

        if violations:
            raise OrchestrationPolicyError("; ".join(violations))

        return self


class AutonomousOrchestrationPolicy(BaseModel):
    """Top-level policy for M5.3 mission orchestration."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = "1.0"
    budgets: OrchestrationBudgetPolicy = Field(
        default_factory=OrchestrationBudgetPolicy
    )
    safety: OrchestrationSafetyPolicy = Field(
        default_factory=OrchestrationSafetyPolicy
    )
'@

Write-Utf8NoBom "forge\autonomous_orchestration\models.py" @'
"""Immutable contracts for autonomous mission orchestration."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, model_validator

from forge.autonomous_orchestration.states import (
    IterationOutcome,
    OrchestrationState,
    OrchestrationStopKind,
    RESUMABLE_ORCHESTRATION_STATES,
    TERMINAL_ORCHESTRATION_STATES,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class FrozenOrchestrationContract(BaseModel):
    """Base immutable orchestration contract."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class OrchestrationRequest(FrozenOrchestrationContract):
    """Request to start or simulate mission orchestration."""

    request_id: str = Field(min_length=1)
    schema_version: str = "1.0"
    mission_id: str = Field(min_length=1)
    repository_root: str = Field(min_length=1)
    dry_run: bool = True
    maximum_cycles: int = Field(default=25, ge=1, le=500)
    requested_by: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=utc_now)


class MissionSession(FrozenOrchestrationContract):
    """Versioned state of one mission-orchestration session."""

    session_id: str = Field(min_length=1)
    schema_version: str = "1.0"
    mission_id: str = Field(min_length=1)
    plan_id: str = Field(min_length=1)
    plan_version: int = Field(ge=1)
    repository_root: str = Field(min_length=1)
    state: OrchestrationState = OrchestrationState.CREATED
    current_step_id: str | None = None
    completed_step_ids: tuple[str, ...] = ()
    failed_step_ids: tuple[str, ...] = ()
    cycle_count: int = Field(default=0, ge=0)
    execution_count: int = Field(default=0, ge=0)
    retry_count: int = Field(default=0, ge=0)
    rollback_count: int = Field(default=0, ge=0)
    replan_count: int = Field(default=0, ge=0)
    checkpoint_id: str | None = None
    stop_reason: str | None = None
    version: int = Field(default=1, ge=1)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_session_invariants(
        self,
    ) -> MissionSession:
        completed = set(self.completed_step_ids)
        failed = set(self.failed_step_ids)

        if len(completed) != len(self.completed_step_ids):
            raise ValueError(
                "completed_step_ids cannot contain duplicates."
            )

        if len(failed) != len(self.failed_step_ids):
            raise ValueError(
                "failed_step_ids cannot contain duplicates."
            )

        overlap = completed.intersection(failed)
        if overlap:
            raise ValueError(
                "A step cannot be both completed and failed."
            )

        if (
            self.current_step_id is not None
            and self.current_step_id in completed
        ):
            raise ValueError(
                "Current step cannot already be completed."
            )

        if (
            self.state in TERMINAL_ORCHESTRATION_STATES
            and self.stop_reason is None
        ):
            raise ValueError(
                "Terminal orchestration session requires stop_reason."
            )

        return self


class OrchestrationIteration(FrozenOrchestrationContract):
    """Immutable record of one bounded orchestration iteration."""

    iteration_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    sequence: int = Field(ge=1)
    mission_version_before: int = Field(ge=1)
    mission_version_after: int | None = Field(default=None, ge=1)
    selected_step_id: str | None = None
    execution_request_id: str | None = None
    execution_id: str | None = None
    outcome: IterationOutcome
    recovery_action: str | None = None
    evidence_ids: tuple[str, ...] = ()
    event_ids: tuple[str, ...] = ()
    started_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None

    @model_validator(mode="after")
    def validate_iteration_execution_limit(
        self,
    ) -> OrchestrationIteration:
        if (
            self.execution_id is not None
            and self.execution_request_id is None
        ):
            raise ValueError(
                "Execution result requires an execution request."
            )

        if (
            self.outcome
            in {
                IterationOutcome.STEP_SUCCEEDED,
                IterationOutcome.STEP_FAILED,
                IterationOutcome.DRY_RUN_COMPLETED,
            }
            and self.execution_id is None
        ):
            raise ValueError(
                "Execution outcome requires execution_id."
            )

        return self


class SessionCheckpoint(FrozenOrchestrationContract):
    """Restart-safe orchestration session checkpoint."""

    checkpoint_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    mission_id: str = Field(min_length=1)
    session_version: int = Field(ge=1)
    mission_snapshot_version: int = Field(ge=1)
    plan_version: int = Field(ge=1)
    repository_fingerprint: str = Field(min_length=1)
    current_step_id: str | None = None
    completed_step_ids: tuple[str, ...] = ()
    verified: bool = False
    created_at: datetime = Field(default_factory=utc_now)


class OrchestrationStop(FrozenOrchestrationContract):
    """Explicit reason the orchestrator stopped."""

    stop_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    stop_kind: OrchestrationStopKind
    reason: str = Field(min_length=1)
    approval_required: bool = False
    resumable: bool = False
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_resumability(
        self,
    ) -> OrchestrationStop:
        if (
            self.stop_kind
            in {
                OrchestrationStopKind.COMPLETED,
                OrchestrationStopKind.FAILED,
                OrchestrationStopKind.CANCELLED,
            }
            and self.resumable
        ):
            raise ValueError(
                "Terminal orchestration stops cannot be resumable."
            )

        return self


def session_is_resumable(
    session: MissionSession,
) -> bool:
    """Return whether the session state may enter resume validation."""
    return session.state in RESUMABLE_ORCHESTRATION_STATES
'@

Write-Utf8NoBom "forge\autonomous_orchestration\__init__.py" @'
"""Aerion Forge autonomous mission orchestrator contracts."""

from forge.autonomous_orchestration.errors import (
    AutonomousOrchestrationError,
    OrchestrationContractError,
    OrchestrationIdentifierError,
    OrchestrationPolicyError,
    OrchestrationResumeError,
    OrchestrationStateError,
)
from forge.autonomous_orchestration.identifiers import (
    mission_session_identifier,
    orchestration_iteration_identifier,
    orchestration_request_identifier,
    orchestration_stop_identifier,
    session_checkpoint_identifier,
)
from forge.autonomous_orchestration.models import (
    MissionSession,
    OrchestrationIteration,
    OrchestrationRequest,
    OrchestrationStop,
    SessionCheckpoint,
    session_is_resumable,
)
from forge.autonomous_orchestration.policies import (
    AutonomousOrchestrationPolicy,
    OrchestrationBudgetPolicy,
    OrchestrationSafetyPolicy,
)
from forge.autonomous_orchestration.states import (
    IterationOutcome,
    OrchestrationState,
    OrchestrationStopKind,
    RESUMABLE_ORCHESTRATION_STATES,
    TERMINAL_ORCHESTRATION_STATES,
)

__all__ = [
    "AutonomousOrchestrationError",
    "AutonomousOrchestrationPolicy",
    "IterationOutcome",
    "MissionSession",
    "OrchestrationBudgetPolicy",
    "OrchestrationContractError",
    "OrchestrationIdentifierError",
    "OrchestrationIteration",
    "OrchestrationPolicyError",
    "OrchestrationRequest",
    "OrchestrationResumeError",
    "OrchestrationSafetyPolicy",
    "OrchestrationState",
    "OrchestrationStateError",
    "OrchestrationStop",
    "OrchestrationStopKind",
    "RESUMABLE_ORCHESTRATION_STATES",
    "SessionCheckpoint",
    "TERMINAL_ORCHESTRATION_STATES",
    "mission_session_identifier",
    "orchestration_iteration_identifier",
    "orchestration_request_identifier",
    "orchestration_stop_identifier",
    "session_checkpoint_identifier",
    "session_is_resumable",
]
'@

Write-Utf8NoBom "tests\test_autonomous_orchestration_identifiers.py" @'
from forge.autonomous_orchestration.identifiers import (
    mission_session_identifier,
    orchestration_request_identifier,
)


def test_orchestration_request_identifier_is_stable() -> None:
    first = orchestration_request_identifier(
        {
            "mission_id": "mission-1",
            "repository_root": "repository",
        }
    )
    second = orchestration_request_identifier(
        {
            "repository_root": "repository",
            "mission_id": "mission-1",
        }
    )

    assert first == second
    assert first.startswith("orchestration-request-")


def test_mission_session_identifier_has_prefix() -> None:
    result = mission_session_identifier(
        {
            "mission_id": "mission-1",
            "plan_id": "plan-1",
        }
    )

    assert result.startswith("mission-session-")
'@

Write-Utf8NoBom "tests\test_autonomous_orchestration_states.py" @'
from forge.autonomous_orchestration.states import (
    OrchestrationState,
    RESUMABLE_ORCHESTRATION_STATES,
    TERMINAL_ORCHESTRATION_STATES,
)


def test_terminal_states_are_explicit() -> None:
    assert OrchestrationState.COMPLETED in TERMINAL_ORCHESTRATION_STATES
    assert OrchestrationState.FAILED in TERMINAL_ORCHESTRATION_STATES
    assert OrchestrationState.READY not in TERMINAL_ORCHESTRATION_STATES


def test_paused_session_is_resumable() -> None:
    assert OrchestrationState.PAUSED in RESUMABLE_ORCHESTRATION_STATES
    assert (
        OrchestrationState.COMPLETED
        not in RESUMABLE_ORCHESTRATION_STATES
    )
'@

Write-Utf8NoBom "tests\test_autonomous_orchestration_policies.py" @'
import pytest
from pydantic import ValidationError

from forge.autonomous_orchestration.errors import (
    OrchestrationPolicyError,
)
from forge.autonomous_orchestration.policies import (
    AutonomousOrchestrationPolicy,
    OrchestrationBudgetPolicy,
    OrchestrationSafetyPolicy,
)


def test_default_policy_is_bounded_and_safe() -> None:
    policy = AutonomousOrchestrationPolicy()

    assert policy.safety.dry_run_by_default
    assert policy.safety.one_execution_per_iteration
    assert policy.budgets.maximum_cycles >= (
        policy.budgets.maximum_step_executions
    )


def test_cycles_must_cover_step_executions() -> None:
    with pytest.raises(ValidationError):
        OrchestrationBudgetPolicy(
            maximum_cycles=5,
            maximum_step_executions=10,
        )


def test_unsafe_replay_policy_is_rejected() -> None:
    with pytest.raises(OrchestrationPolicyError):
        OrchestrationSafetyPolicy(
            allow_completed_step_replay=True,
        )
'@

Write-Utf8NoBom "tests\test_autonomous_orchestration_models.py" @'
import pytest
from pydantic import ValidationError

from forge.autonomous_orchestration.models import (
    MissionSession,
    OrchestrationIteration,
    OrchestrationStop,
    session_is_resumable,
)
from forge.autonomous_orchestration.states import (
    IterationOutcome,
    OrchestrationState,
    OrchestrationStopKind,
)


def session(
    *,
    state: OrchestrationState = OrchestrationState.CREATED,
    stop_reason: str | None = None,
) -> MissionSession:
    return MissionSession(
        session_id="session-1",
        mission_id="mission-1",
        plan_id="plan-1",
        plan_version=1,
        repository_root="repository",
        state=state,
        stop_reason=stop_reason,
    )


def test_terminal_session_requires_stop_reason() -> None:
    with pytest.raises(ValidationError):
        session(state=OrchestrationState.COMPLETED)


def test_completed_step_cannot_be_current_step() -> None:
    with pytest.raises(ValidationError):
        MissionSession(
            session_id="session-1",
            mission_id="mission-1",
            plan_id="plan-1",
            plan_version=1,
            repository_root="repository",
            current_step_id="step-1",
            completed_step_ids=("step-1",),
        )


def test_execution_outcome_requires_execution_id() -> None:
    with pytest.raises(ValidationError):
        OrchestrationIteration(
            iteration_id="iteration-1",
            session_id="session-1",
            sequence=1,
            mission_version_before=1,
            outcome=IterationOutcome.STEP_SUCCEEDED,
        )


def test_terminal_stop_cannot_be_resumable() -> None:
    with pytest.raises(ValidationError):
        OrchestrationStop(
            stop_id="stop-1",
            session_id="session-1",
            stop_kind=OrchestrationStopKind.COMPLETED,
            reason="Mission completed.",
            resumable=True,
        )


def test_paused_session_is_resumable() -> None:
    assert session_is_resumable(
        session(state=OrchestrationState.PAUSED)
    )
'@

Write-Host ""
Write-Host "M5.3 Package 0 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check . --fix
Assert-CommandSuccess "Ruff fix"

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_autonomous_orchestration_identifiers.py `
    .\tests\test_autonomous_orchestration_states.py `
    .\tests\test_autonomous_orchestration_policies.py `
    .\tests\test_autonomous_orchestration_models.py `
    -p no:cacheprovider
Assert-CommandSuccess "M5.3 Package 0 focused tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M5.3 PACKAGE 0 COMPLETE" -ForegroundColor Green

git status --short
