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

$ExpectedBranch = "feature/m5.7-autonomous-execution-engine"
$CurrentBranch = git branch --show-current
Assert-CommandSuccess "Read current branch"

if ($CurrentBranch -ne $ExpectedBranch) {
    throw "M5.7 Package 0 must run on '$ExpectedBranch'. Current branch: '$CurrentBranch'."
}

Write-Utf8NoBom "forge\autonomous_execution_v2\errors.py" @'
"""Errors for M5.7 autonomous execution."""

from __future__ import annotations


class AutonomousExecutionV2Error(Exception):
    """Base M5.7 execution error."""


class ExecutionContractError(AutonomousExecutionV2Error):
    """Raised when an execution contract is invalid."""


class ExecutionStateError(AutonomousExecutionV2Error):
    """Raised for an invalid execution transition."""


class ExecutionPolicyError(AutonomousExecutionV2Error):
    """Raised when execution violates policy."""


class ExecutionAuthorityError(AutonomousExecutionV2Error):
    """Raised when execution authority is insufficient."""
'@

Write-Utf8NoBom "forge\autonomous_execution_v2\states.py" @'
"""Enumerations for M5.7 autonomous execution."""

from __future__ import annotations

from enum import StrEnum


class ExecutionRunState(StrEnum):
    CREATED = "created"
    VALIDATING = "validating"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    RECOVERING = "recovering"
    AWAITING_APPROVAL = "awaiting_approval"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExecutionStepState(StrEnum):
    PENDING = "pending"
    ELIGIBLE = "eligible"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class ExecutionAttemptState(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RecoveryAction(StrEnum):
    RETRY = "retry"
    PAUSE = "pause"
    SKIP = "skip"
    ROLLBACK = "rollback"
    REPLAN = "replan"
    ABORT = "abort"


class EvidenceKind(StrEnum):
    TOOL_RESULT = "tool_result"
    TEST_RESULT = "test_result"
    VALIDATION_RESULT = "validation_result"
    FILE_CHANGE = "file_change"
    CHECKPOINT = "checkpoint"
    REPORT = "report"
'@

Write-Utf8NoBom "forge\autonomous_execution_v2\identifiers.py" @'
"""Deterministic identifiers for M5.7 execution."""

from __future__ import annotations

import hashlib
import json
from enum import Enum
from pathlib import Path
from typing import Any


def _normalize(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, dict):
        return {
            str(key): _normalize(item)
            for key, item in sorted(
                value.items(),
                key=lambda pair: str(pair[0]),
            )
        }
    if isinstance(value, list | tuple | set | frozenset):
        items = [_normalize(item) for item in value]
        if isinstance(value, set | frozenset):
            items = sorted(
                items,
                key=lambda item: json.dumps(
                    item,
                    sort_keys=True,
                    separators=(",", ":"),
                ),
            )
        return items
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    raise TypeError(
        f"Unsupported identifier value: {type(value)!r}"
    )


def deterministic_identifier(
    prefix: str,
    payload: dict[str, Any],
) -> str:
    canonical = json.dumps(
        _normalize(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    digest = hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()[:24]
    return f"{prefix}-{digest}"


def execution_request_identifier(
    payload: dict[str, Any],
) -> str:
    return deterministic_identifier("execution-request-v2", payload)


def execution_run_identifier(
    payload: dict[str, Any],
) -> str:
    return deterministic_identifier("execution-run-v2", payload)


def execution_step_identifier(
    payload: dict[str, Any],
) -> str:
    return deterministic_identifier("execution-step-v2", payload)


def execution_attempt_identifier(
    payload: dict[str, Any],
) -> str:
    return deterministic_identifier("execution-attempt-v2", payload)


def execution_evidence_identifier(
    payload: dict[str, Any],
) -> str:
    return deterministic_identifier("execution-evidence-v2", payload)
'@

Write-Utf8NoBom "forge\autonomous_execution_v2\policies.py" @'
"""Default-safe policies for M5.7 execution."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ExecutionLimits(BaseModel):
    model_config = ConfigDict(frozen=True)

    maximum_steps: int = Field(default=100, ge=1, le=1000)
    maximum_attempts_per_step: int = Field(
        default=3,
        ge=1,
        le=20,
    )
    maximum_evidence_items: int = Field(
        default=1000,
        ge=1,
        le=10000,
    )


class ExecutionSafetyPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    require_approved_plan: bool = True
    require_repository_scope_match: bool = True
    require_evidence_for_success: bool = True
    allow_destructive_execution: bool = False
    require_approval_for_high_risk: bool = True
    stop_on_blocking_failure: bool = True


class AutonomousExecutionV2Policy(BaseModel):
    model_config = ConfigDict(frozen=True)

    limits: ExecutionLimits = Field(
        default_factory=ExecutionLimits
    )
    safety: ExecutionSafetyPolicy = Field(
        default_factory=ExecutionSafetyPolicy
    )
'@

Write-Utf8NoBom "forge\autonomous_execution_v2\models.py" @'
"""Immutable M5.7 autonomous execution contracts."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, model_validator

from forge.autonomous_execution_v2.errors import ExecutionContractError
from forge.autonomous_execution_v2.states import (
    EvidenceKind,
    ExecutionAttemptState,
    ExecutionRunState,
    ExecutionStepState,
    RecoveryAction,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ExecutionRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    request_id: str
    plan_id: str
    plan_version: int = Field(ge=1)
    repository_root: str
    repository_fingerprint: str
    requested_by: str
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_request(self) -> "ExecutionRequest":
        if not self.plan_id.strip():
            raise ExecutionContractError("Plan ID cannot be empty.")
        if not self.repository_root.strip():
            raise ExecutionContractError(
                "Repository root cannot be empty."
            )
        if not self.requested_by.strip():
            raise ExecutionContractError(
                "Execution requester cannot be empty."
            )
        return self


class ExecutionDependency(BaseModel):
    model_config = ConfigDict(frozen=True)

    dependency_id: str
    source_step_id: str
    target_step_id: str
    rationale: str

    @model_validator(mode="after")
    def validate_dependency(self) -> "ExecutionDependency":
        if self.source_step_id == self.target_step_id:
            raise ExecutionContractError(
                "Execution step cannot depend on itself."
            )
        if not self.rationale.strip():
            raise ExecutionContractError(
                "Dependency rationale cannot be empty."
            )
        return self


class ExecutionStep(BaseModel):
    model_config = ConfigDict(frozen=True)

    step_id: str
    planning_step_id: str
    sequence: int = Field(ge=1)
    name: str
    description: str
    state: ExecutionStepState = ExecutionStepState.PENDING
    required_tools: tuple[str, ...] = ()
    expected_outputs: tuple[str, ...] = ()
    acceptance_criteria: tuple[str, ...] = ()
    risk: str = "low"
    requires_approval: bool = False
    destructive: bool = False

    @model_validator(mode="after")
    def validate_step(self) -> "ExecutionStep":
        if not self.name.strip():
            raise ExecutionContractError(
                "Execution step name cannot be empty."
            )
        if not self.description.strip():
            raise ExecutionContractError(
                "Execution step description cannot be empty."
            )
        if self.destructive and not self.requires_approval:
            raise ExecutionContractError(
                "Destructive execution requires approval."
            )
        return self


class ExecutionAttempt(BaseModel):
    model_config = ConfigDict(frozen=True)

    attempt_id: str
    run_id: str
    step_id: str
    attempt_number: int = Field(ge=1)
    state: ExecutionAttemptState = ExecutionAttemptState.CREATED
    tool_invocation_ids: tuple[str, ...] = ()
    failure_reason: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class ExecutionEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    evidence_id: str
    run_id: str
    step_id: str
    attempt_id: str
    kind: EvidenceKind
    references: tuple[str, ...]
    summary: str
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_evidence(self) -> "ExecutionEvidence":
        if not self.references:
            raise ExecutionContractError(
                "Execution evidence requires references."
            )
        if not self.summary.strip():
            raise ExecutionContractError(
                "Execution evidence summary cannot be empty."
            )
        return self


class RecoveryDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    decision_id: str
    run_id: str
    step_id: str
    attempt_id: str
    action: RecoveryAction
    rationale: str
    approved_by: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class ExecutionRun(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    request_id: str
    plan_id: str
    plan_version: int = Field(ge=1)
    repository_root: str
    repository_fingerprint: str
    state: ExecutionRunState = ExecutionRunState.CREATED
    steps: tuple[ExecutionStep, ...]
    dependencies: tuple[ExecutionDependency, ...] = ()
    current_step_id: str | None = None
    failure_reason: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_run(self) -> "ExecutionRun":
        if not self.steps:
            raise ExecutionContractError(
                "Execution run requires at least one step."
            )

        step_ids = [step.step_id for step in self.steps]

        if len(step_ids) != len(set(step_ids)):
            raise ExecutionContractError(
                "Execution step IDs must be unique."
            )

        known = set(step_ids)

        for dependency in self.dependencies:
            if (
                dependency.source_step_id not in known
                or dependency.target_step_id not in known
            ):
                raise ExecutionContractError(
                    "Execution dependency references unknown step."
                )

        return self
'@

Write-Utf8NoBom "forge\autonomous_execution_v2\__init__.py" @'
"""M5.7 autonomous execution contracts."""

from forge.autonomous_execution_v2.errors import (
    AutonomousExecutionV2Error,
    ExecutionAuthorityError,
    ExecutionContractError,
    ExecutionPolicyError,
    ExecutionStateError,
)
from forge.autonomous_execution_v2.identifiers import (
    execution_attempt_identifier,
    execution_evidence_identifier,
    execution_request_identifier,
    execution_run_identifier,
    execution_step_identifier,
)
from forge.autonomous_execution_v2.models import (
    ExecutionAttempt,
    ExecutionDependency,
    ExecutionEvidence,
    ExecutionRequest,
    ExecutionRun,
    ExecutionStep,
    RecoveryDecision,
)
from forge.autonomous_execution_v2.policies import (
    AutonomousExecutionV2Policy,
    ExecutionLimits,
    ExecutionSafetyPolicy,
)
from forge.autonomous_execution_v2.states import (
    EvidenceKind,
    ExecutionAttemptState,
    ExecutionRunState,
    ExecutionStepState,
    RecoveryAction,
)

__all__ = [
    "AutonomousExecutionV2Error",
    "AutonomousExecutionV2Policy",
    "EvidenceKind",
    "ExecutionAttempt",
    "ExecutionAttemptState",
    "ExecutionAuthorityError",
    "ExecutionContractError",
    "ExecutionDependency",
    "ExecutionEvidence",
    "ExecutionLimits",
    "ExecutionPolicyError",
    "ExecutionRequest",
    "ExecutionRun",
    "ExecutionRunState",
    "ExecutionSafetyPolicy",
    "ExecutionStateError",
    "ExecutionStep",
    "ExecutionStepState",
    "RecoveryAction",
    "RecoveryDecision",
    "execution_attempt_identifier",
    "execution_evidence_identifier",
    "execution_request_identifier",
    "execution_run_identifier",
    "execution_step_identifier",
]
'@

Write-Utf8NoBom "tests\test_autonomous_execution_v2_identifiers.py" @'
from forge.autonomous_execution_v2.identifiers import (
    execution_run_identifier,
    execution_step_identifier,
)


def test_identifiers_are_deterministic() -> None:
    payload = {"plan_id": "plan-1", "paths": {"b.py", "a.py"}}

    assert execution_run_identifier(
        payload
    ) == execution_run_identifier(payload)


def test_identifier_prefixes_are_distinct() -> None:
    payload = {"step": "step-1"}

    assert execution_run_identifier(
        payload
    ).startswith("execution-run-v2-")

    assert execution_step_identifier(
        payload
    ).startswith("execution-step-v2-")
'@

Write-Utf8NoBom "tests\test_autonomous_execution_v2_states.py" @'
from forge.autonomous_execution_v2.states import (
    EvidenceKind,
    ExecutionAttemptState,
    ExecutionRunState,
    ExecutionStepState,
    RecoveryAction,
)


def test_state_values_are_stable() -> None:
    assert ExecutionRunState.READY.value == "ready"
    assert ExecutionStepState.ELIGIBLE.value == "eligible"
    assert ExecutionAttemptState.RUNNING.value == "running"
    assert RecoveryAction.REPLAN.value == "replan"
    assert EvidenceKind.TEST_RESULT.value == "test_result"
'@

Write-Utf8NoBom "tests\test_autonomous_execution_v2_policies.py" @'
from forge.autonomous_execution_v2.policies import (
    AutonomousExecutionV2Policy,
)


def test_default_policy_is_safe() -> None:
    policy = AutonomousExecutionV2Policy()

    assert policy.safety.require_approved_plan
    assert policy.safety.require_evidence_for_success
    assert not policy.safety.allow_destructive_execution
    assert policy.limits.maximum_attempts_per_step == 3
'@

Write-Utf8NoBom "tests\test_autonomous_execution_v2_models.py" @'
import pytest

from forge.autonomous_execution_v2.errors import ExecutionContractError
from forge.autonomous_execution_v2.models import (
    ExecutionDependency,
    ExecutionEvidence,
    ExecutionRequest,
    ExecutionRun,
    ExecutionStep,
)
from forge.autonomous_execution_v2.states import EvidenceKind


def step(step_id: str, sequence: int) -> ExecutionStep:
    return ExecutionStep(
        step_id=step_id,
        planning_step_id=f"planning-{step_id}",
        sequence=sequence,
        name=f"Step {sequence}",
        description="Execute a repository-grounded action.",
    )


def test_request_rejects_empty_plan_id() -> None:
    with pytest.raises(ExecutionContractError):
        ExecutionRequest(
            request_id="request-1",
            plan_id="",
            plan_version=1,
            repository_root="repository",
            repository_fingerprint="fingerprint",
            requested_by="Aerion",
        )


def test_run_accepts_known_dependency() -> None:
    run = ExecutionRun(
        run_id="run-1",
        request_id="request-1",
        plan_id="plan-1",
        plan_version=1,
        repository_root="repository",
        repository_fingerprint="fingerprint",
        steps=(
            step("step-1", 1),
            step("step-2", 2),
        ),
        dependencies=(
            ExecutionDependency(
                dependency_id="dependency-1",
                source_step_id="step-2",
                target_step_id="step-1",
                rationale="Step two requires step one.",
            ),
        ),
    )

    assert len(run.steps) == 2


def test_evidence_requires_references() -> None:
    with pytest.raises(ExecutionContractError):
        ExecutionEvidence(
            evidence_id="evidence-1",
            run_id="run-1",
            step_id="step-1",
            attempt_id="attempt-1",
            kind=EvidenceKind.TEST_RESULT,
            references=(),
            summary="Tests passed.",
        )
'@

Write-Host ""
Write-Host "M5.7 Package 0 files written. Running validation..." `
    -ForegroundColor Cyan

python -m ruff check . --fix
Assert-CommandSuccess "Ruff fix"

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_autonomous_execution_v2_identifiers.py `
    .\tests\test_autonomous_execution_v2_states.py `
    .\tests\test_autonomous_execution_v2_policies.py `
    .\tests\test_autonomous_execution_v2_models.py `
    -p no:cacheprovider
Assert-CommandSuccess "M5.7 Package 0 focused tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full repository tests"

Write-Host ""
Write-Host "M5.7 PACKAGE 0 COMPLETE" -ForegroundColor Green

git status --short
