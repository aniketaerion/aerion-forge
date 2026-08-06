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
    throw "M5.2 Package 0 must run on '$ExpectedBranch'. Current branch: '$CurrentBranch'."
}

Write-Utf8NoBom "forge\autonomous_execution\errors.py" @'
"""Typed errors for the autonomous execution engine."""

from __future__ import annotations


class AutonomousExecutionError(RuntimeError):
    """Base error for autonomous execution failures."""


class ExecutionContractError(AutonomousExecutionError):
    """Raised when an execution contract is invalid."""


class ExecutionIdentifierError(AutonomousExecutionError):
    """Raised when an execution identifier cannot be created."""


class ExecutionPolicyError(AutonomousExecutionError):
    """Raised when an execution policy is invalid."""


class ToolContractError(AutonomousExecutionError):
    """Raised when a tool contract is invalid."""


class ToolResolutionError(AutonomousExecutionError):
    """Raised when a tool cannot be resolved safely."""
'@

Write-Utf8NoBom "forge\autonomous_execution\states.py" @'
"""Autonomous execution engine enumerations."""

from __future__ import annotations

from enum import StrEnum


class StepExecutionState(StrEnum):
    """Authoritative execution states for one mission step."""

    PENDING = "pending"
    ELIGIBILITY_CHECK = "eligibility_check"
    READY = "ready"
    LEASE_ACQUIRING = "lease_acquiring"
    CHECKPOINT_VERIFYING = "checkpoint_verifying"
    TOOL_PREPARING = "tool_preparing"
    TOOL_RUNNING = "tool_running"
    EFFECT_VERIFYING = "effect_verifying"
    EVIDENCE_RECORDING = "evidence_recording"
    SUCCEEDED = "succeeded"
    BLOCKED = "blocked"
    AWAITING_APPROVAL = "awaiting_approval"
    RETRY_PENDING = "retry_pending"
    ROLLBACK_PENDING = "rollback_pending"
    ROLLED_BACK = "rolled_back"
    PAUSED = "paused"
    ESCALATED = "escalated"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ToolExecutionStatus(StrEnum):
    """Tool invocation status."""

    PENDING = "pending"
    VALIDATING = "validating"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"
    DRY_RUN = "dry_run"


class ExecutionFailureClass(StrEnum):
    """Failure classes defined by the M5.2 architecture."""

    ELIGIBILITY_FAILURE = "eligibility_failure"
    DEPENDENCY_FAILURE = "dependency_failure"
    AUTHORITY_FAILURE = "authority_failure"
    APPROVAL_FAILURE = "approval_failure"
    LEASE_FAILURE = "lease_failure"
    CHECKPOINT_FAILURE = "checkpoint_failure"
    TOOL_RESOLUTION_FAILURE = "tool_resolution_failure"
    ARGUMENT_VALIDATION_FAILURE = "argument_validation_failure"
    TOOL_TIMEOUT = "tool_timeout"
    TOOL_EXIT_FAILURE = "tool_exit_failure"
    SCOPE_VIOLATION = "scope_violation"
    EVIDENCE_FAILURE = "evidence_failure"
    INVARIANT_VIOLATION = "invariant_violation"
    ROLLBACK_FAILURE = "rollback_failure"


TERMINAL_EXECUTION_STATES: frozenset[StepExecutionState] = frozenset(
    {
        StepExecutionState.SUCCEEDED,
        StepExecutionState.FAILED,
        StepExecutionState.CANCELLED,
    }
)
'@

Write-Utf8NoBom "forge\autonomous_execution\identifiers.py" @'
"""Deterministic identifiers for autonomous execution records."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from forge.autonomous_execution.errors import ExecutionIdentifierError
from forge.autonomous_runtime.identifiers import deterministic_identifier


def _identifier(
    prefix: str,
    payload: Mapping[str, Any],
) -> str:
    try:
        return deterministic_identifier(prefix, payload)
    except Exception as exc:  # pragma: no cover - defensive boundary
        raise ExecutionIdentifierError(
            f"Unable to create {prefix} identifier."
        ) from exc


def execution_request_identifier(
    payload: Mapping[str, Any],
) -> str:
    return _identifier("execution-request", payload)


def execution_lease_identifier(
    payload: Mapping[str, Any],
) -> str:
    return _identifier("execution-lease", payload)


def tool_invocation_identifier(
    payload: Mapping[str, Any],
) -> str:
    return _identifier("tool-invocation", payload)


def step_execution_identifier(
    payload: Mapping[str, Any],
) -> str:
    return _identifier("step-execution", payload)


def execution_evidence_identifier(
    payload: Mapping[str, Any],
) -> str:
    return _identifier("execution-evidence", payload)
'@

Write-Utf8NoBom "forge\autonomous_execution\policies.py" @'
"""Bounded policies for autonomous execution."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from forge.autonomous_execution.errors import ExecutionPolicyError
from forge.autonomous_runtime.states import AuthorityLevel, RiskClass


class ExecutionBudgetPolicy(BaseModel):
    """Finite execution budgets."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    maximum_step_attempts: int = Field(default=2, ge=1, le=10)
    maximum_tool_invocations_per_step: int = Field(
        default=8,
        ge=1,
        le=100,
    )
    maximum_execution_seconds: int = Field(
        default=900,
        ge=1,
        le=86400,
    )
    maximum_lease_seconds: int = Field(
        default=1200,
        ge=30,
        le=86400,
    )
    maximum_affected_files: int = Field(
        default=50,
        ge=1,
        le=1000,
    )

    @model_validator(mode="after")
    def validate_time_relationships(
        self,
    ) -> ExecutionBudgetPolicy:
        if self.maximum_lease_seconds < self.maximum_execution_seconds:
            raise ValueError(
                "maximum_lease_seconds must cover "
                "maximum_execution_seconds."
            )
        return self


class ToolGatewayPolicy(BaseModel):
    """Default-safe tool-gateway policy."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    allow_network_access: bool = False
    allow_unrestricted_shell: bool = False
    allow_dynamic_tool_import: bool = False
    require_registered_tools: bool = True
    require_argument_validation: bool = True
    require_effect_verification: bool = True
    require_checkpoint_for_mutation: bool = True
    redact_secrets: bool = True
    dry_run_by_default: bool = True

    @model_validator(mode="after")
    def validate_safety_invariants(
        self,
    ) -> ToolGatewayPolicy:
        violations: list[str] = []

        if self.allow_network_access:
            violations.append("network access must be denied by default")
        if self.allow_unrestricted_shell:
            violations.append("unrestricted shell must remain disabled")
        if self.allow_dynamic_tool_import:
            violations.append("dynamic tool import must remain disabled")
        if not self.require_registered_tools:
            violations.append("registered tools are mandatory")
        if not self.require_argument_validation:
            violations.append("argument validation is mandatory")
        if not self.require_effect_verification:
            violations.append("effect verification is mandatory")
        if not self.require_checkpoint_for_mutation:
            violations.append(
                "checkpoint-before-mutation is mandatory"
            )
        if not self.redact_secrets:
            violations.append("secret redaction is mandatory")

        if violations:
            raise ExecutionPolicyError("; ".join(violations))

        return self


class ExecutionAuthorityPolicy(BaseModel):
    """Execution-specific authority constraints."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    autonomous_ceiling: AuthorityLevel = AuthorityLevel.A2_MODIFY
    explicit_approval_from: AuthorityLevel = AuthorityLevel.A4_COMMIT
    high_risk_from: RiskClass = RiskClass.R3_HIGH

    @model_validator(mode="after")
    def validate_order(
        self,
    ) -> ExecutionAuthorityPolicy:
        if self.autonomous_ceiling >= self.explicit_approval_from:
            raise ValueError(
                "Autonomous ceiling must stay below "
                "the explicit approval boundary."
            )
        return self


class AutonomousExecutionPolicy(BaseModel):
    """Top-level execution-engine policy."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = "1.0"
    budgets: ExecutionBudgetPolicy = Field(
        default_factory=ExecutionBudgetPolicy
    )
    gateway: ToolGatewayPolicy = Field(
        default_factory=ToolGatewayPolicy
    )
    authority: ExecutionAuthorityPolicy = Field(
        default_factory=ExecutionAuthorityPolicy
    )
    single_writer_required: bool = True
    one_tool_at_a_time: bool = True

    @model_validator(mode="after")
    def validate_runtime_invariants(
        self,
    ) -> AutonomousExecutionPolicy:
        violations: list[str] = []

        if not self.single_writer_required:
            violations.append("single-writer execution is mandatory")
        if not self.one_tool_at_a_time:
            violations.append("one-tool-at-a-time is mandatory")

        if violations:
            raise ExecutionPolicyError("; ".join(violations))

        return self
'@

Write-Utf8NoBom "forge\autonomous_execution\tool_contracts.py" @'
"""Contracts for the controlled autonomous tool gateway."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from forge.autonomous_execution.states import ToolExecutionStatus
from forge.autonomous_runtime.states import AuthorityLevel, RiskClass


class FrozenToolContract(BaseModel):
    """Base immutable tool contract."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class ToolDefinition(FrozenToolContract):
    """Registered tool metadata and safety contract."""

    tool_name: str = Field(min_length=1)
    action_kinds: tuple[str, ...] = Field(min_length=1)
    authority_required: AuthorityLevel
    risk_class: RiskClass
    mutates_repository: bool = False
    requires_checkpoint: bool = False
    timeout_seconds: int = Field(default=300, ge=1, le=86400)
    argument_schema: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_checkpoint_requirement(
        self,
    ) -> ToolDefinition:
        if self.mutates_repository and not self.requires_checkpoint:
            raise ValueError(
                "Mutating tools require a checkpoint."
            )
        return self


class ToolExecutionRequest(FrozenToolContract):
    """One controlled tool invocation request."""

    invocation_id: str = Field(min_length=1)
    mission_id: str = Field(min_length=1)
    step_id: str = Field(min_length=1)
    tool_name: str = Field(min_length=1)
    action_kind: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)
    approved_scope: tuple[str, ...] = ()
    checkpoint_id: str | None = None
    approval_id: str | None = None
    dry_run: bool = True


class ToolExecutionResult(FrozenToolContract):
    """Immutable controlled tool result."""

    invocation_id: str = Field(min_length=1)
    status: ToolExecutionStatus
    exit_code: int | None = None
    stdout_reference: str | None = None
    stderr_reference: str | None = None
    affected_files: tuple[str, ...] = ()
    result_digest: str | None = None
    started_at: str = Field(min_length=1)
    completed_at: str | None = None
'@

Write-Utf8NoBom "forge\autonomous_execution\models.py" @'
"""Immutable contracts for autonomous execution."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, model_validator

from forge.autonomous_execution.states import (
    ExecutionFailureClass,
    StepExecutionState,
    TERMINAL_EXECUTION_STATES,
)
from forge.autonomous_execution.tool_contracts import (
    ToolExecutionResult,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class FrozenExecutionContract(BaseModel):
    """Base immutable execution contract."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class ExecutionRequest(FrozenExecutionContract):
    request_id: str = Field(min_length=1)
    schema_version: str = "1.0"
    mission_id: str = Field(min_length=1)
    plan_id: str = Field(min_length=1)
    step_id: str = Field(min_length=1)
    repository_root: str = Field(min_length=1)
    dry_run: bool = True
    requested_by: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=utc_now)


class ExecutionLease(FrozenExecutionContract):
    lease_id: str = Field(min_length=1)
    mission_id: str = Field(min_length=1)
    repository_root: str = Field(min_length=1)
    holder: str = Field(min_length=1)
    acquired_at: datetime = Field(default_factory=utc_now)
    expires_at: datetime
    released_at: datetime | None = None
    version: int = Field(default=1, ge=1)

    @model_validator(mode="after")
    def validate_time_order(self) -> ExecutionLease:
        if self.expires_at <= self.acquired_at:
            raise ValueError(
                "Execution lease must expire after acquisition."
            )
        if (
            self.released_at is not None
            and self.released_at < self.acquired_at
        ):
            raise ValueError(
                "Execution lease cannot be released "
                "before acquisition."
            )
        return self


class ExecutionEvidence(FrozenExecutionContract):
    evidence_id: str = Field(min_length=1)
    execution_id: str = Field(min_length=1)
    invocation_id: str | None = None
    evidence_kind: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    artifact_references: tuple[str, ...] = ()
    repository_fingerprint: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=utc_now)


class StepExecutionRecord(FrozenExecutionContract):
    execution_id: str = Field(min_length=1)
    mission_id: str = Field(min_length=1)
    step_id: str = Field(min_length=1)
    attempt_number: int = Field(default=1, ge=1)
    lease_id: str | None = None
    checkpoint_id: str | None = None
    invocation_results: tuple[ToolExecutionResult, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    state: StepExecutionState = StepExecutionState.PENDING
    failure_class: ExecutionFailureClass | None = None
    started_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None

    @model_validator(mode="after")
    def validate_terminal_record(
        self,
    ) -> StepExecutionRecord:
        if self.state in TERMINAL_EXECUTION_STATES:
            if self.completed_at is None:
                raise ValueError(
                    "Terminal execution requires completed_at."
                )
            if (
                self.state is StepExecutionState.SUCCEEDED
                and not self.evidence_ids
            ):
                raise ValueError(
                    "Successful execution requires evidence."
                )
        return self
'@

Write-Utf8NoBom "forge\autonomous_execution\__init__.py" @'
"""Aerion Forge autonomous execution engine contracts."""

from forge.autonomous_execution.errors import (
    AutonomousExecutionError,
    ExecutionContractError,
    ExecutionIdentifierError,
    ExecutionPolicyError,
    ToolContractError,
    ToolResolutionError,
)
from forge.autonomous_execution.identifiers import (
    execution_evidence_identifier,
    execution_lease_identifier,
    execution_request_identifier,
    step_execution_identifier,
    tool_invocation_identifier,
)
from forge.autonomous_execution.models import (
    ExecutionEvidence,
    ExecutionLease,
    ExecutionRequest,
    StepExecutionRecord,
)
from forge.autonomous_execution.policies import (
    AutonomousExecutionPolicy,
    ExecutionAuthorityPolicy,
    ExecutionBudgetPolicy,
    ToolGatewayPolicy,
)
from forge.autonomous_execution.states import (
    ExecutionFailureClass,
    StepExecutionState,
    TERMINAL_EXECUTION_STATES,
    ToolExecutionStatus,
)
from forge.autonomous_execution.tool_contracts import (
    ToolDefinition,
    ToolExecutionRequest,
    ToolExecutionResult,
)

__all__ = [
    "AutonomousExecutionError",
    "AutonomousExecutionPolicy",
    "ExecutionAuthorityPolicy",
    "ExecutionBudgetPolicy",
    "ExecutionContractError",
    "ExecutionEvidence",
    "ExecutionFailureClass",
    "ExecutionIdentifierError",
    "ExecutionLease",
    "ExecutionPolicyError",
    "ExecutionRequest",
    "StepExecutionRecord",
    "StepExecutionState",
    "TERMINAL_EXECUTION_STATES",
    "ToolContractError",
    "ToolDefinition",
    "ToolExecutionRequest",
    "ToolExecutionResult",
    "ToolExecutionStatus",
    "ToolGatewayPolicy",
    "ToolResolutionError",
    "execution_evidence_identifier",
    "execution_lease_identifier",
    "execution_request_identifier",
    "step_execution_identifier",
    "tool_invocation_identifier",
]
'@

Write-Utf8NoBom "tests\test_autonomous_execution_identifiers.py" @'
from forge.autonomous_execution.identifiers import (
    execution_request_identifier,
    tool_invocation_identifier,
)


def test_execution_request_identifier_is_stable() -> None:
    first = execution_request_identifier(
        {
            "mission_id": "mission-1",
            "step_id": "step-1",
        }
    )
    second = execution_request_identifier(
        {
            "step_id": "step-1",
            "mission_id": "mission-1",
        }
    )

    assert first == second
    assert first.startswith("execution-request-")


def test_tool_invocation_identifier_has_prefix() -> None:
    result = tool_invocation_identifier(
        {
            "mission_id": "mission-1",
            "tool_name": "ruff",
        }
    )

    assert result.startswith("tool-invocation-")
'@

Write-Utf8NoBom "tests\test_autonomous_execution_models.py" @'
from datetime import timedelta

import pytest
from pydantic import ValidationError

from forge.autonomous_execution.models import (
    ExecutionLease,
    StepExecutionRecord,
    utc_now,
)
from forge.autonomous_execution.states import StepExecutionState


def test_execution_lease_requires_valid_time_order() -> None:
    acquired = utc_now()

    with pytest.raises(ValidationError):
        ExecutionLease(
            lease_id="lease-1",
            mission_id="mission-1",
            repository_root="repository",
            holder="runtime",
            acquired_at=acquired,
            expires_at=acquired - timedelta(seconds=1),
        )


def test_successful_execution_requires_evidence() -> None:
    with pytest.raises(ValidationError):
        StepExecutionRecord(
            execution_id="execution-1",
            mission_id="mission-1",
            step_id="step-1",
            state=StepExecutionState.SUCCEEDED,
            completed_at=utc_now(),
        )
'@

Write-Utf8NoBom "tests\test_autonomous_execution_policies.py" @'
import pytest
from pydantic import ValidationError

from forge.autonomous_execution.errors import ExecutionPolicyError
from forge.autonomous_execution.policies import (
    AutonomousExecutionPolicy,
    ExecutionBudgetPolicy,
    ToolGatewayPolicy,
)


def test_default_execution_policy_is_safe() -> None:
    policy = AutonomousExecutionPolicy()

    assert policy.single_writer_required
    assert policy.one_tool_at_a_time
    assert policy.gateway.dry_run_by_default
    assert not policy.gateway.allow_unrestricted_shell


def test_lease_budget_must_cover_execution_budget() -> None:
    with pytest.raises(ValidationError):
        ExecutionBudgetPolicy(
            maximum_execution_seconds=1000,
            maximum_lease_seconds=900,
        )


def test_unsafe_gateway_policy_is_rejected() -> None:
    with pytest.raises(ExecutionPolicyError):
        ToolGatewayPolicy(
            allow_unrestricted_shell=True,
        )
'@

Write-Utf8NoBom "tests\test_autonomous_execution_tool_contracts.py" @'
import pytest
from pydantic import ValidationError

from forge.autonomous_execution.states import ToolExecutionStatus
from forge.autonomous_execution.tool_contracts import (
    ToolDefinition,
    ToolExecutionRequest,
    ToolExecutionResult,
)
from forge.autonomous_runtime.states import AuthorityLevel, RiskClass


def test_mutating_tool_requires_checkpoint() -> None:
    with pytest.raises(ValidationError):
        ToolDefinition(
            tool_name="file-editor",
            action_kinds=("apply_patch",),
            authority_required=AuthorityLevel.A2_MODIFY,
            risk_class=RiskClass.R2_MODERATE,
            mutates_repository=True,
            requires_checkpoint=False,
        )


def test_dry_run_request_defaults_safe() -> None:
    request = ToolExecutionRequest(
        invocation_id="invocation-1",
        mission_id="mission-1",
        step_id="step-1",
        tool_name="ruff",
        action_kind="validate",
    )

    assert request.dry_run


def test_tool_result_is_immutable_contract() -> None:
    result = ToolExecutionResult(
        invocation_id="invocation-1",
        status=ToolExecutionStatus.SUCCEEDED,
        exit_code=0,
        started_at="2026-08-06T00:00:00+00:00",
        completed_at="2026-08-06T00:00:01+00:00",
    )

    assert result.exit_code == 0
'@

Write-Host ""
Write-Host "M5.2 Package 0 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check . --fix
Assert-CommandSuccess "Ruff fix"

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_autonomous_execution_identifiers.py `
    .\tests\test_autonomous_execution_models.py `
    .\tests\test_autonomous_execution_policies.py `
    .\tests\test_autonomous_execution_tool_contracts.py `
    -p no:cacheprovider
Assert-CommandSuccess "M5.2 Package 0 focused tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M5.2 PACKAGE 0 COMPLETE" -ForegroundColor Green

git status --short