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
    throw "M5.1 Package 0 must run on '$ExpectedBranch'. Current branch: '$CurrentBranch'."
}

Write-Utf8NoBom "forge\autonomous_runtime\errors.py" @'
"""Typed errors for the Aerion Forge autonomous runtime."""

from __future__ import annotations


class AutonomousRuntimeError(RuntimeError):
    """Base error for autonomous-runtime failures."""


class MissionContractError(AutonomousRuntimeError):
    """Raised when a mission contract is invalid."""


class MissionIdentifierError(AutonomousRuntimeError):
    """Raised when a deterministic identifier cannot be created."""


class MissionPolicyError(AutonomousRuntimeError):
    """Raised when an execution or authority policy is invalid."""


class MissionStateError(AutonomousRuntimeError):
    """Raised when a mission state value or invariant is invalid."""
'@

Write-Utf8NoBom "forge\autonomous_runtime\states.py" @'
"""Autonomous runtime enumerations."""

from __future__ import annotations

from enum import IntEnum, StrEnum


class MissionState(StrEnum):
    """Authoritative autonomous mission states."""

    RECEIVED = "received"
    QUALIFYING = "qualifying"
    CLARIFICATION_REQUIRED = "clarification_required"
    QUALIFIED = "qualified"
    CONTEXT_BUILDING = "context_building"
    CONTEXT_READY = "context_ready"
    PLANNING = "planning"
    PLAN_READY = "plan_ready"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    EXECUTING = "executing"
    VALIDATING = "validating"
    REVIEWING = "reviewing"
    PAUSED = "paused"
    BLOCKED = "blocked"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"
    ESCALATED = "escalated"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MissionDecision(StrEnum):
    """Qualification decisions."""

    ACCEPT = "accept"
    REQUEST_CLARIFICATION = "request_clarification"
    REJECT = "reject"
    ESCALATE = "escalate"


class RiskClass(IntEnum):
    """Ordered mission and action risk classes."""

    R0_READ_ONLY = 0
    R1_LOW = 1
    R2_MODERATE = 2
    R3_HIGH = 3
    R4_CRITICAL = 4
    R5_HUMAN_CONTROLLED = 5


class AuthorityLevel(IntEnum):
    """Ordered autonomous authority levels."""

    A0_READ = 0
    A1_PLAN = 1
    A2_MODIFY = 2
    A3_EXECUTE = 3
    A4_COMMIT = 4
    A5_PUSH = 5
    A6_MERGE_RELEASE = 6


class StepStatus(StrEnum):
    """Mission-step lifecycle status."""

    PENDING = "pending"
    READY = "ready"
    AWAITING_APPROVAL = "awaiting_approval"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"
    ROLLED_BACK = "rolled_back"
    CANCELLED = "cancelled"


class ValidationStatus(StrEnum):
    """Validation evidence status."""

    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"
    SKIP = "skip"
    UNAVAILABLE = "unavailable"
    ERROR = "error"


class ReviewDecision(StrEnum):
    """Independent mission-review decisions."""

    APPROVE = "approve"
    REVISE = "revise"
    ESCALATE = "escalate"
    REJECT = "reject"


class RecoveryAction(StrEnum):
    """Recovery actions available to the runtime."""

    RETRY_STEP = "retry_step"
    REPLAN = "replan"
    ROLLBACK_STEP = "rollback_step"
    ROLLBACK_MISSION = "rollback_mission"
    PAUSE = "pause"
    ESCALATE = "escalate"
    ABORT = "abort"


TERMINAL_MISSION_STATES: frozenset[MissionState] = frozenset(
    {
        MissionState.COMPLETED,
        MissionState.FAILED,
        MissionState.CANCELLED,
    }
)
'@

Write-Utf8NoBom "forge\autonomous_runtime\identifiers.py" @'
"""Deterministic identifiers for autonomous-runtime records."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from forge.autonomous_runtime.errors import MissionIdentifierError


def _normalize(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, Mapping):
        return {
            str(key): _normalize(item)
            for key, item in sorted(
                value.items(),
                key=lambda pair: str(pair[0]),
            )
        }
    if isinstance(value, Sequence) and not isinstance(
        value,
        (str, bytes, bytearray),
    ):
        return [_normalize(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value

    raise MissionIdentifierError(
        f"Unsupported identifier value: {type(value).__name__}"
    )


def deterministic_identifier(
    prefix: str,
    payload: Mapping[str, Any],
) -> str:
    """Create a stable identifier from a JSON-compatible payload."""
    normalized_prefix = prefix.strip().lower().replace("_", "-")

    if not normalized_prefix:
        raise MissionIdentifierError(
            "Identifier prefix must not be empty."
        )

    encoded = json.dumps(
        _normalize(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    digest = hashlib.sha256(encoded).hexdigest()[:24]

    return f"{normalized_prefix}-{digest}"


def mission_request_identifier(payload: Mapping[str, Any]) -> str:
    return deterministic_identifier("mission-request", payload)


def mission_identifier(payload: Mapping[str, Any]) -> str:
    return deterministic_identifier("mission", payload)


def mission_context_identifier(payload: Mapping[str, Any]) -> str:
    return deterministic_identifier("mission-context", payload)


def mission_plan_identifier(payload: Mapping[str, Any]) -> str:
    return deterministic_identifier("mission-plan", payload)


def mission_step_identifier(payload: Mapping[str, Any]) -> str:
    return deterministic_identifier("mission-step", payload)


def mission_event_identifier(payload: Mapping[str, Any]) -> str:
    return deterministic_identifier("mission-event", payload)


def mission_checkpoint_identifier(payload: Mapping[str, Any]) -> str:
    return deterministic_identifier("mission-checkpoint", payload)


def validation_evidence_identifier(payload: Mapping[str, Any]) -> str:
    return deterministic_identifier("validation-evidence", payload)


def mission_outcome_identifier(payload: Mapping[str, Any]) -> str:
    return deterministic_identifier("mission-outcome", payload)
'@

Write-Utf8NoBom "forge\autonomous_runtime\policies.py" @'
"""Bounded execution and authority policies."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from forge.autonomous_runtime.errors import MissionPolicyError
from forge.autonomous_runtime.states import (
    AuthorityLevel,
    RiskClass,
)


class RuntimeBudgetPolicy(BaseModel):
    """Finite mission execution budgets."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    maximum_steps: int = Field(default=20, ge=1, le=500)
    maximum_attempts_per_step: int = Field(default=2, ge=1, le=10)
    maximum_replans: int = Field(default=2, ge=0, le=10)
    maximum_rollback_attempts: int = Field(default=1, ge=0, le=5)
    maximum_tool_calls: int = Field(default=200, ge=1, le=5000)
    maximum_execution_cycles: int = Field(default=20, ge=1, le=500)
    time_budget_seconds: int = Field(default=3600, ge=30, le=604800)

    @model_validator(mode="after")
    def validate_relationships(self) -> RuntimeBudgetPolicy:
        if self.maximum_execution_cycles < self.maximum_steps:
            raise ValueError(
                "maximum_execution_cycles must be at least maximum_steps."
            )
        return self


class AuthorityPolicy(BaseModel):
    """Default authority ceiling and explicit-approval boundary."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    autonomous_ceiling: AuthorityLevel = AuthorityLevel.A2_MODIFY
    automatic_validation_authority: AuthorityLevel = (
        AuthorityLevel.A3_EXECUTE
    )
    explicit_approval_from: AuthorityLevel = AuthorityLevel.A4_COMMIT
    high_risk_from: RiskClass = RiskClass.R3_HIGH

    @model_validator(mode="after")
    def validate_authority_order(self) -> AuthorityPolicy:
        if (
            self.autonomous_ceiling
            >= self.explicit_approval_from
        ):
            raise ValueError(
                "Autonomous authority ceiling must remain below "
                "the explicit-approval boundary."
            )
        return self


class AutonomousRuntimePolicy(BaseModel):
    """Top-level immutable runtime policy."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = "1.0"
    budgets: RuntimeBudgetPolicy = Field(
        default_factory=RuntimeBudgetPolicy
    )
    authority: AuthorityPolicy = Field(
        default_factory=AuthorityPolicy
    )
    network_access_allowed: bool = False
    unrestricted_shell_allowed: bool = False
    unrestricted_mutation_allowed: bool = False
    require_verified_checkpoint_for_mutation: bool = True
    require_read_only_reviewer: bool = True
    single_writer_required: bool = True

    @model_validator(mode="after")
    def validate_safety_invariants(self) -> AutonomousRuntimePolicy:
        violations: list[str] = []

        if self.network_access_allowed:
            violations.append("network access must be denied by default")
        if self.unrestricted_shell_allowed:
            violations.append("unrestricted shell must remain disabled")
        if self.unrestricted_mutation_allowed:
            violations.append(
                "unrestricted autonomous mutation must remain disabled"
            )
        if not self.require_verified_checkpoint_for_mutation:
            violations.append(
                "verified checkpoints are required before mutation"
            )
        if not self.require_read_only_reviewer:
            violations.append("the reviewer must remain read-only")
        if not self.single_writer_required:
            violations.append("M5.1 requires a single writer")

        if violations:
            raise MissionPolicyError("; ".join(violations))

        return self
'@

Write-Utf8NoBom "forge\autonomous_runtime\models.py" @'
"""Immutable contracts for the Aerion Forge autonomous runtime."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from forge.autonomous_runtime.policies import RuntimeBudgetPolicy
from forge.autonomous_runtime.states import (
    AuthorityLevel,
    MissionDecision,
    MissionState,
    RecoveryAction,
    ReviewDecision,
    RiskClass,
    StepStatus,
    ValidationStatus,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class FrozenContract(BaseModel):
    """Base class for immutable autonomous-runtime contracts."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        use_enum_values=False,
    )


class MissionRequest(FrozenContract):
    request_id: str = Field(min_length=1)
    schema_version: str = "1.0"
    objective: str = Field(min_length=1)
    repository_root: str = Field(min_length=1)
    requested_scope: tuple[str, ...] = ()
    excluded_scope: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    acceptance_criteria: tuple[str, ...] = ()
    requested_authority: AuthorityLevel = AuthorityLevel.A1_PLAN
    budgets: RuntimeBudgetPolicy = Field(
        default_factory=RuntimeBudgetPolicy
    )
    requested_by: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_scope(self) -> MissionRequest:
        overlap = set(self.requested_scope).intersection(
            self.excluded_scope
        )
        if overlap:
            raise ValueError(
                "Requested and excluded scope overlap: "
                + ", ".join(sorted(overlap))
            )
        return self


class MissionContext(FrozenContract):
    context_id: str = Field(min_length=1)
    mission_id: str = Field(min_length=1)
    repository_fingerprint: str = Field(min_length=1)
    relevant_files: tuple[str, ...] = ()
    relevant_symbols: tuple[str, ...] = ()
    dependency_edges: tuple[tuple[str, str], ...] = ()
    architecture_constraints: tuple[str, ...] = ()
    business_rules: tuple[str, ...] = ()
    existing_tests: tuple[str, ...] = ()
    validation_commands: tuple[str, ...] = ()
    known_risks: tuple[str, ...] = ()
    knowledge_references: tuple[str, ...] = ()
    source_provenance: tuple[str, ...] = ()
    created_at: datetime = Field(default_factory=utc_now)


class MissionStep(FrozenContract):
    step_id: str = Field(min_length=1)
    plan_id: str = Field(min_length=1)
    sequence: int = Field(ge=1)
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    status: StepStatus = StepStatus.PENDING
    action_kind: str = Field(min_length=1)
    preconditions: tuple[str, ...] = ()
    expected_outputs: tuple[str, ...] = ()
    expected_files: tuple[str, ...] = ()
    prohibited_files: tuple[str, ...] = ()
    required_authority: AuthorityLevel = AuthorityLevel.A1_PLAN
    risk_class: RiskClass = RiskClass.R1_LOW
    approval_required: bool = False
    validation_requirements: tuple[str, ...] = ()
    checkpoint_required: bool = False
    attempt_budget: int = Field(default=2, ge=1, le=10)
    timeout_seconds: int = Field(default=300, ge=1, le=86400)
    depends_on: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_file_scope(self) -> MissionStep:
        overlap = set(self.expected_files).intersection(
            self.prohibited_files
        )
        if overlap:
            raise ValueError(
                "Expected and prohibited files overlap: "
                + ", ".join(sorted(overlap))
            )
        if (
            self.required_authority >= AuthorityLevel.A2_MODIFY
            and not self.checkpoint_required
        ):
            raise ValueError(
                "Modifying steps require a checkpoint."
            )
        return self


class MissionPlan(FrozenContract):
    plan_id: str = Field(min_length=1)
    mission_id: str = Field(min_length=1)
    version: int = Field(default=1, ge=1)
    objective_summary: str = Field(min_length=1)
    steps: tuple[MissionStep, ...] = ()
    expected_files: tuple[str, ...] = ()
    prohibited_files: tuple[str, ...] = ()
    required_validations: tuple[str, ...] = ()
    completion_criteria: tuple[str, ...] = Field(min_length=1)
    risk_class: RiskClass = RiskClass.R1_LOW
    required_authority: AuthorityLevel = AuthorityLevel.A1_PLAN
    created_at: datetime = Field(default_factory=utc_now)
    approved_at: datetime | None = None

    @model_validator(mode="after")
    def validate_plan(self) -> MissionPlan:
        sequences = [step.sequence for step in self.steps]
        if len(sequences) != len(set(sequences)):
            raise ValueError("Mission step sequences must be unique.")
        overlap = set(self.expected_files).intersection(
            self.prohibited_files
        )
        if overlap:
            raise ValueError(
                "Plan expected and prohibited files overlap."
            )
        highest_authority = max(
            (
                step.required_authority
                for step in self.steps
            ),
            default=AuthorityLevel.A0_READ,
        )
        if self.required_authority < highest_authority:
            raise ValueError(
                "Plan authority is below a step authority requirement."
            )
        return self


class ApprovalDecision(FrozenContract):
    approval_id: str = Field(min_length=1)
    mission_id: str = Field(min_length=1)
    plan_id: str | None = None
    step_id: str | None = None
    decision: str = Field(min_length=1)
    authority_granted: AuthorityLevel
    scope: tuple[str, ...] = ()
    conditions: tuple[str, ...] = ()
    approved_by: str = Field(min_length=1)
    issued_at: datetime = Field(default_factory=utc_now)
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    reason: str = ""

    @property
    def active(self) -> bool:
        now = utc_now()
        return (
            self.revoked_at is None
            and (
                self.expires_at is None
                or self.expires_at > now
            )
        )


class ToolInvocation(FrozenContract):
    invocation_id: str = Field(min_length=1)
    mission_id: str = Field(min_length=1)
    step_id: str = Field(min_length=1)
    tool_name: str = Field(min_length=1)
    action_kind: str = Field(min_length=1)
    arguments_digest: str = Field(min_length=1)
    redacted_arguments: dict[str, Any] = Field(default_factory=dict)
    required_authority: AuthorityLevel
    approval_id: str | None = None
    started_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None
    exit_code: int | None = None
    stdout_reference: str | None = None
    stderr_reference: str | None = None
    affected_files: tuple[str, ...] = ()
    result_digest: str | None = None
    status: str = "pending"


class ValidationEvidence(FrozenContract):
    evidence_id: str = Field(min_length=1)
    mission_id: str = Field(min_length=1)
    step_id: str | None = None
    check_name: str = Field(min_length=1)
    check_kind: str = Field(min_length=1)
    required: bool = True
    status: ValidationStatus
    command: str | None = None
    exit_code: int | None = None
    summary: str = ""
    metrics: dict[str, int | float | str | bool] = Field(
        default_factory=dict
    )
    artifact_references: tuple[str, ...] = ()
    repository_fingerprint: str = Field(min_length=1)
    started_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None


class MissionCheckpoint(FrozenContract):
    checkpoint_id: str = Field(min_length=1)
    mission_id: str = Field(min_length=1)
    step_id: str | None = None
    kind: str = Field(min_length=1)
    repository_fingerprint: str = Field(min_length=1)
    git_head: str | None = None
    working_tree_digest: str = Field(min_length=1)
    file_snapshot_references: tuple[str, ...] = ()
    created_at: datetime = Field(default_factory=utc_now)
    verified: bool = False
    restoration_test: str | None = None


class MissionEvent(FrozenContract):
    event_id: str = Field(min_length=1)
    schema_version: str = "1.0"
    mission_id: str = Field(min_length=1)
    sequence: int = Field(ge=1)
    event_type: str = Field(min_length=1)
    previous_state: MissionState | None = None
    new_state: MissionState
    actor: str = Field(min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str | None = None
    causation_id: str | None = None
    occurred_at: datetime = Field(default_factory=utc_now)


class RecoveryDecision(FrozenContract):
    recovery_id: str = Field(min_length=1)
    mission_id: str = Field(min_length=1)
    step_id: str | None = None
    failure_class: str = Field(min_length=1)
    action: RecoveryAction
    checkpoint_id: str | None = None
    attempt_number: int = Field(ge=1)
    reason: str = Field(min_length=1)
    approved_by: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class MissionOutcome(FrozenContract):
    outcome_id: str = Field(min_length=1)
    mission_id: str = Field(min_length=1)
    terminal_state: MissionState
    objective_satisfied: bool
    completed_step_ids: tuple[str, ...] = ()
    changed_files: tuple[str, ...] = ()
    validation_evidence_ids: tuple[str, ...] = ()
    unresolved_findings: tuple[str, ...] = ()
    review_decision: ReviewDecision
    report_references: tuple[str, ...] = ()
    completed_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_terminal_outcome(self) -> MissionOutcome:
        if self.terminal_state not in {
            MissionState.COMPLETED,
            MissionState.FAILED,
            MissionState.CANCELLED,
        }:
            raise ValueError(
                "Mission outcome requires a terminal state."
            )
        if (
            self.terminal_state is MissionState.COMPLETED
            and (
                not self.objective_satisfied
                or self.review_decision is not ReviewDecision.APPROVE
                or self.unresolved_findings
            )
        ):
            raise ValueError(
                "Completed outcomes require objective satisfaction, "
                "approved review, and no unresolved findings."
            )
        return self


class AutonomousMission(FrozenContract):
    mission_id: str = Field(min_length=1)
    schema_version: str = "1.0"
    version: int = Field(default=1, ge=1)
    request: MissionRequest
    state: MissionState = MissionState.RECEIVED
    qualification_decision: MissionDecision | None = None
    risk_class: RiskClass = RiskClass.R0_READ_ONLY
    granted_authority: AuthorityLevel = AuthorityLevel.A0_READ
    approval_state: str = "not_required"
    context_id: str | None = None
    plan_id: str | None = None
    current_step_id: str | None = None
    attempt_count: int = Field(default=0, ge=0)
    replan_count: int = Field(default=0, ge=0)
    tool_call_count: int = Field(default=0, ge=0)
    checkpoint_ids: tuple[str, ...] = ()
    event_sequence: int = Field(default=0, ge=0)
    validation_evidence_ids: tuple[str, ...] = ()
    finding_ids: tuple[str, ...] = ()
    outcome_id: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_authority(self) -> AutonomousMission:
        if self.granted_authority > self.request.requested_authority:
            raise ValueError(
                "Granted authority exceeds requested authority."
            )
        if (
            self.state in {
                MissionState.COMPLETED,
                MissionState.FAILED,
                MissionState.CANCELLED,
            }
            and self.outcome_id is None
        ):
            raise ValueError(
                "Terminal missions require an outcome identifier."
            )
        return self
'@

Write-Utf8NoBom "forge\autonomous_runtime\__init__.py" @'
"""Aerion Forge autonomous runtime contracts."""

from forge.autonomous_runtime.errors import (
    AutonomousRuntimeError,
    MissionContractError,
    MissionIdentifierError,
    MissionPolicyError,
    MissionStateError,
)
from forge.autonomous_runtime.identifiers import (
    deterministic_identifier,
    mission_checkpoint_identifier,
    mission_context_identifier,
    mission_event_identifier,
    mission_identifier,
    mission_outcome_identifier,
    mission_plan_identifier,
    mission_request_identifier,
    mission_step_identifier,
    validation_evidence_identifier,
)
from forge.autonomous_runtime.models import (
    ApprovalDecision,
    AutonomousMission,
    MissionCheckpoint,
    MissionContext,
    MissionEvent,
    MissionOutcome,
    MissionPlan,
    MissionRequest,
    MissionStep,
    RecoveryDecision,
    ToolInvocation,
    ValidationEvidence,
)
from forge.autonomous_runtime.policies import (
    AuthorityPolicy,
    AutonomousRuntimePolicy,
    RuntimeBudgetPolicy,
)
from forge.autonomous_runtime.states import (
    TERMINAL_MISSION_STATES,
    AuthorityLevel,
    MissionDecision,
    MissionState,
    RecoveryAction,
    ReviewDecision,
    RiskClass,
    StepStatus,
    ValidationStatus,
)

__all__ = [
    "ApprovalDecision",
    "AuthorityLevel",
    "AuthorityPolicy",
    "AutonomousMission",
    "AutonomousRuntimeError",
    "AutonomousRuntimePolicy",
    "MissionCheckpoint",
    "MissionContext",
    "MissionContractError",
    "MissionDecision",
    "MissionEvent",
    "MissionIdentifierError",
    "MissionOutcome",
    "MissionPlan",
    "MissionPolicyError",
    "MissionRequest",
    "MissionState",
    "MissionStateError",
    "MissionStep",
    "RecoveryAction",
    "RecoveryDecision",
    "ReviewDecision",
    "RiskClass",
    "RuntimeBudgetPolicy",
    "StepStatus",
    "TERMINAL_MISSION_STATES",
    "ToolInvocation",
    "ValidationEvidence",
    "ValidationStatus",
    "deterministic_identifier",
    "mission_checkpoint_identifier",
    "mission_context_identifier",
    "mission_event_identifier",
    "mission_identifier",
    "mission_outcome_identifier",
    "mission_plan_identifier",
    "mission_request_identifier",
    "mission_step_identifier",
    "validation_evidence_identifier",
]
'@

Write-Utf8NoBom "tests\test_autonomous_runtime_identifiers.py" @'
import pytest

from forge.autonomous_runtime.errors import MissionIdentifierError
from forge.autonomous_runtime.identifiers import (
    deterministic_identifier,
    mission_identifier,
)


def test_deterministic_identifier_is_stable() -> None:
    first = mission_identifier(
        {"objective": "Create mission contracts", "version": 1}
    )
    second = mission_identifier(
        {"version": 1, "objective": "Create mission contracts"}
    )

    assert first == second
    assert first.startswith("mission-")


def test_identifier_rejects_unsupported_values() -> None:
    with pytest.raises(MissionIdentifierError):
        deterministic_identifier(
            "mission",
            {"unsupported": object()},
        )
'@

Write-Utf8NoBom "tests\test_autonomous_runtime_states.py" @'
from forge.autonomous_runtime.states import (
    TERMINAL_MISSION_STATES,
    AuthorityLevel,
    MissionState,
    RiskClass,
)


def test_terminal_mission_states_are_explicit() -> None:
    assert TERMINAL_MISSION_STATES == {
        MissionState.COMPLETED,
        MissionState.FAILED,
        MissionState.CANCELLED,
    }


def test_authority_and_risk_are_ordered() -> None:
    assert AuthorityLevel.A0_READ < AuthorityLevel.A2_MODIFY
    assert AuthorityLevel.A4_COMMIT < AuthorityLevel.A6_MERGE_RELEASE
    assert RiskClass.R2_MODERATE < RiskClass.R4_CRITICAL
'@

Write-Utf8NoBom "tests\test_autonomous_runtime_models.py" @'
from datetime import timedelta

import pytest
from pydantic import ValidationError

from forge.autonomous_runtime.models import (
    ApprovalDecision,
    AutonomousMission,
    MissionOutcome,
    MissionRequest,
    MissionStep,
    utc_now,
)
from forge.autonomous_runtime.states import (
    AuthorityLevel,
    MissionState,
    ReviewDecision,
)


def request() -> MissionRequest:
    return MissionRequest(
        request_id="request-1",
        objective="Implement autonomous runtime contracts.",
        repository_root="D:/Software Dev/Aerion Forge",
        requested_scope=("forge/autonomous_runtime",),
        excluded_scope=("deployments",),
        acceptance_criteria=("All tests pass.",),
        requested_authority=AuthorityLevel.A2_MODIFY,
        requested_by="Aerion",
    )


def test_contracts_are_immutable() -> None:
    mission_request = request()

    with pytest.raises(ValidationError):
        setattr(mission_request, "objective", "Changed")


def test_scope_overlap_is_rejected() -> None:
    with pytest.raises(ValidationError):
        MissionRequest(
            request_id="request-2",
            objective="Invalid scope.",
            repository_root="repository",
            requested_scope=("forge",),
            excluded_scope=("forge",),
            requested_by="Aerion",
        )


def test_modifying_step_requires_checkpoint() -> None:
    with pytest.raises(ValidationError):
        MissionStep(
            step_id="step-1",
            plan_id="plan-1",
            sequence=1,
            title="Modify code",
            description="Modify approved code.",
            action_kind="apply_patch",
            required_authority=AuthorityLevel.A2_MODIFY,
            checkpoint_required=False,
        )


def test_terminal_mission_requires_outcome() -> None:
    with pytest.raises(ValidationError):
        AutonomousMission(
            mission_id="mission-1",
            request=request(),
            state=MissionState.COMPLETED,
            granted_authority=AuthorityLevel.A2_MODIFY,
        )


def test_completed_outcome_requires_approved_review() -> None:
    with pytest.raises(ValidationError):
        MissionOutcome(
            outcome_id="outcome-1",
            mission_id="mission-1",
            terminal_state=MissionState.COMPLETED,
            objective_satisfied=True,
            review_decision=ReviewDecision.REJECT,
        )


def test_approval_activity_uses_expiry_and_revocation() -> None:
    active = ApprovalDecision(
        approval_id="approval-1",
        mission_id="mission-1",
        decision="approve",
        authority_granted=AuthorityLevel.A2_MODIFY,
        approved_by="Aerion",
        expires_at=utc_now() + timedelta(minutes=5),
    )
    expired = ApprovalDecision(
        approval_id="approval-2",
        mission_id="mission-1",
        decision="approve",
        authority_granted=AuthorityLevel.A2_MODIFY,
        approved_by="Aerion",
        expires_at=utc_now() - timedelta(minutes=5),
    )

    assert active.active
    assert not expired.active
'@

Write-Utf8NoBom "tests\test_autonomous_runtime_policies.py" @'
import pytest
from pydantic import ValidationError

from forge.autonomous_runtime.errors import MissionPolicyError
from forge.autonomous_runtime.policies import (
    AuthorityPolicy,
    AutonomousRuntimePolicy,
    RuntimeBudgetPolicy,
)
from forge.autonomous_runtime.states import AuthorityLevel


def test_default_runtime_policy_is_bounded_and_safe() -> None:
    policy = AutonomousRuntimePolicy()

    assert policy.budgets.maximum_attempts_per_step == 2
    assert policy.budgets.maximum_replans == 2
    assert not policy.network_access_allowed
    assert not policy.unrestricted_mutation_allowed
    assert policy.single_writer_required


def test_execution_cycles_must_cover_steps() -> None:
    with pytest.raises(ValidationError):
        RuntimeBudgetPolicy(
            maximum_steps=50,
            maximum_execution_cycles=20,
        )


def test_autonomous_ceiling_must_be_below_approval_boundary() -> None:
    with pytest.raises(ValidationError):
        AuthorityPolicy(
            autonomous_ceiling=AuthorityLevel.A4_COMMIT,
            explicit_approval_from=AuthorityLevel.A4_COMMIT,
        )


def test_unsafe_runtime_policy_is_rejected() -> None:
    with pytest.raises(MissionPolicyError):
        AutonomousRuntimePolicy(
            unrestricted_mutation_allowed=True,
        )
'@

Write-Host ""
Write-Host "M5.1 Package 0 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check . --fix
Assert-CommandSuccess "Ruff fix"

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_autonomous_runtime_identifiers.py `
    .\tests\test_autonomous_runtime_states.py `
    .\tests\test_autonomous_runtime_models.py `
    .\tests\test_autonomous_runtime_policies.py `
    -p no:cacheprovider
Assert-CommandSuccess "M5.1 Package 0 focused tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M5.1 PACKAGE 0 COMPLETE" -ForegroundColor Green

git status --short