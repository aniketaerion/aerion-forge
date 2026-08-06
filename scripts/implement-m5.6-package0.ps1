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
    New-Item -ItemType Directory -Path (Split-Path $FullPath -Parent) -Force | Out-Null
    [System.IO.File]::WriteAllText(
        $FullPath,
        $Content,
        [System.Text.UTF8Encoding]::new($false)
    )
    Write-Host "WROTE $Path" -ForegroundColor Green
}

function Assert-Success {
    param([Parameter(Mandatory)][string]$Name)
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

$ExpectedBranch = "feature/m5.6-autonomous-planning-engine"
$CurrentBranch = git branch --show-current
Assert-Success "Read current branch"

if ($CurrentBranch -ne $ExpectedBranch) {
    throw "M5.6 Package 0 must run on '$ExpectedBranch'. Current branch: '$CurrentBranch'."
}

Write-Utf8NoBom "forge\autonomous_planning\errors.py" @'
"""Errors raised by the autonomous planning engine."""

class AutonomousPlanningError(Exception):
    """Base error for autonomous planning."""


class PlanningContractError(AutonomousPlanningError):
    """Raised when a planning contract is invalid."""


class PlanningPolicyError(AutonomousPlanningError):
    """Raised when a plan violates policy."""


class PlanningStateError(AutonomousPlanningError):
    """Raised when a planning state transition is invalid."""


class PlanningScopeError(AutonomousPlanningError):
    """Raised when planning crosses an unauthorized scope."""
'@

Write-Utf8NoBom "forge\autonomous_planning\states.py" @'
"""Enumerations for autonomous planning."""

from enum import StrEnum


class PlanningState(StrEnum):
    CREATED = "created"
    ANALYSING = "analysing"
    GENERATING = "generating"
    VALIDATING = "validating"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    READY = "ready"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PlanningIntent(StrEnum):
    IMPLEMENT_FEATURE = "implement_feature"
    FIX_DEFECT = "fix_defect"
    REFACTOR = "refactor"
    MIGRATE = "migrate"
    VALIDATE = "validate"
    INVESTIGATE = "investigate"
    DOCUMENT = "document"
    RELEASE = "release"


class PlanningRisk(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class StepKind(StrEnum):
    ANALYSIS = "analysis"
    CODE_CHANGE = "code_change"
    TEST = "test"
    VALIDATION = "validation"
    DOCUMENTATION = "documentation"
    APPROVAL = "approval"
    RELEASE = "release"


class DependencyKind(StrEnum):
    REQUIRES = "requires"
    BLOCKS = "blocks"
    ORDERS_AFTER = "orders_after"
    OPTIONAL = "optional"


class ApprovalRequirement(StrEnum):
    NONE = "none"
    PLAN = "plan"
    CODE = "code"
    RELEASE = "release"
'@

Write-Utf8NoBom "forge\autonomous_planning\identifiers.py" @'
"""Deterministic identifiers for autonomous planning."""

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
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
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
    raise TypeError(f"Unsupported identifier value: {type(value)!r}")


def deterministic_identifier(prefix: str, payload: dict[str, Any]) -> str:
    canonical = json.dumps(
        _normalize(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]
    return f"{prefix}-{digest}"


def planning_request_identifier(payload: dict[str, Any]) -> str:
    return deterministic_identifier("planning-request", payload)


def planning_session_identifier(payload: dict[str, Any]) -> str:
    return deterministic_identifier("planning-session", payload)


def planning_step_identifier(payload: dict[str, Any]) -> str:
    return deterministic_identifier("planning-step", payload)


def planning_plan_identifier(payload: dict[str, Any]) -> str:
    return deterministic_identifier("planning-plan", payload)


def planning_dependency_identifier(payload: dict[str, Any]) -> str:
    return deterministic_identifier("planning-dependency", payload)
'@

Write-Utf8NoBom "forge\autonomous_planning\policies.py" @'
"""Default-safe policies for autonomous planning."""

from pydantic import BaseModel, ConfigDict, Field


class PlanningLimits(BaseModel):
    model_config = ConfigDict(frozen=True)

    maximum_steps: int = Field(default=50, ge=1, le=500)
    maximum_dependencies: int = Field(default=200, ge=0, le=5000)
    maximum_target_paths: int = Field(default=100, ge=1, le=1000)
    maximum_constraints: int = Field(default=100, ge=0, le=1000)


class PlanningSafetyPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    require_repository_scope: bool = True
    require_acceptance_criteria: bool = True
    reject_empty_objective: bool = True
    reject_path_escape: bool = True
    require_approval_for_high_risk: bool = True
    require_approval_for_release: bool = True
    require_validation_step: bool = True
    allow_destructive_steps: bool = False


class PlanningQualityPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    minimum_step_description_length: int = Field(default=10, ge=1, le=500)
    require_unique_step_names: bool = True
    require_dependency_acyclicity: bool = True
    require_deterministic_ordering: bool = True
    require_traceability: bool = True


class AutonomousPlanningPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    limits: PlanningLimits = Field(default_factory=PlanningLimits)
    safety: PlanningSafetyPolicy = Field(default_factory=PlanningSafetyPolicy)
    quality: PlanningQualityPolicy = Field(default_factory=PlanningQualityPolicy)
'@

Write-Utf8NoBom "forge\autonomous_planning\models.py" @'
"""Immutable contracts for autonomous planning."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, model_validator

from forge.autonomous_planning.errors import PlanningContractError
from forge.autonomous_planning.states import (
    ApprovalRequirement,
    DependencyKind,
    PlanningIntent,
    PlanningRisk,
    PlanningState,
    StepKind,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PlanningRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    request_id: str
    objective: str
    repository_root: str
    intent: PlanningIntent
    target_paths: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    acceptance_criteria: tuple[str, ...] = ()
    requested_capabilities: tuple[str, ...] = ()
    created_by: str
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_request(self) -> "PlanningRequest":
        if not self.objective.strip():
            raise PlanningContractError("Planning objective cannot be empty.")
        if not self.repository_root.strip():
            raise PlanningContractError("Repository root cannot be empty.")
        if not self.created_by.strip():
            raise PlanningContractError("Planning creator cannot be empty.")
        return self


class PlanningDependency(BaseModel):
    model_config = ConfigDict(frozen=True)

    dependency_id: str
    source_step_id: str
    target_step_id: str
    kind: DependencyKind
    rationale: str

    @model_validator(mode="after")
    def validate_dependency(self) -> "PlanningDependency":
        if self.source_step_id == self.target_step_id:
            raise PlanningContractError("Planning step cannot depend on itself.")
        if not self.rationale.strip():
            raise PlanningContractError("Dependency rationale cannot be empty.")
        return self


class PlanningStep(BaseModel):
    model_config = ConfigDict(frozen=True)

    step_id: str
    sequence: int = Field(ge=1)
    name: str
    description: str
    kind: StepKind
    target_paths: tuple[str, ...] = ()
    required_capabilities: tuple[str, ...] = ()
    required_tools: tuple[str, ...] = ()
    expected_outputs: tuple[str, ...] = ()
    acceptance_criteria: tuple[str, ...] = ()
    risk: PlanningRisk = PlanningRisk.LOW
    approval_requirement: ApprovalRequirement = ApprovalRequirement.NONE
    destructive: bool = False

    @model_validator(mode="after")
    def validate_step(self) -> "PlanningStep":
        if not self.name.strip():
            raise PlanningContractError("Planning step name cannot be empty.")
        if not self.description.strip():
            raise PlanningContractError("Planning step description cannot be empty.")
        if self.destructive and self.approval_requirement is ApprovalRequirement.NONE:
            raise PlanningContractError("Destructive step requires explicit approval.")
        return self


class PlanningPlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    plan_id: str
    request_id: str
    version: int = Field(default=1, ge=1)
    state: PlanningState = PlanningState.CREATED
    summary: str
    steps: tuple[PlanningStep, ...]
    dependencies: tuple[PlanningDependency, ...] = ()
    risk: PlanningRisk = PlanningRisk.LOW
    requires_approval: bool = False
    warnings: tuple[str, ...] = ()
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_plan(self) -> "PlanningPlan":
        if not self.summary.strip():
            raise PlanningContractError("Planning summary cannot be empty.")
        if not self.steps:
            raise PlanningContractError("Planning plan requires at least one step.")
        step_ids = [step.step_id for step in self.steps]
        if len(step_ids) != len(set(step_ids)):
            raise PlanningContractError("Planning step identifiers must be unique.")
        sequences = [step.sequence for step in self.steps]
        if sequences != sorted(sequences):
            raise PlanningContractError("Planning steps must be sequence ordered.")
        known = set(step_ids)
        for dependency in self.dependencies:
            if (
                dependency.source_step_id not in known
                or dependency.target_step_id not in known
            ):
                raise PlanningContractError(
                    "Planning dependency references unknown step."
                )
        return self


class PlanningSession(BaseModel):
    model_config = ConfigDict(frozen=True)

    session_id: str
    request_id: str
    state: PlanningState = PlanningState.CREATED
    plan_id: str | None = None
    plan_version: int | None = None
    failure_reason: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class PlanningValidationFinding(BaseModel):
    model_config = ConfigDict(frozen=True)

    finding_id: str
    severity: PlanningRisk
    code: str
    message: str
    step_id: str | None = None
    blocking: bool = False


class PlanningValidationResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    plan_id: str
    valid: bool
    findings: tuple[PlanningValidationFinding, ...] = ()
    validated_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_result(self) -> "PlanningValidationResult":
        if self.valid and any(finding.blocking for finding in self.findings):
            raise PlanningContractError(
                "Valid plan cannot contain blocking findings."
            )
        return self
'@

Write-Utf8NoBom "forge\autonomous_planning\__init__.py" @'
"""Autonomous planning engine contracts."""

from forge.autonomous_planning.errors import (
    AutonomousPlanningError,
    PlanningContractError,
    PlanningPolicyError,
    PlanningScopeError,
    PlanningStateError,
)
from forge.autonomous_planning.identifiers import (
    planning_dependency_identifier,
    planning_plan_identifier,
    planning_request_identifier,
    planning_session_identifier,
    planning_step_identifier,
)
from forge.autonomous_planning.models import (
    PlanningDependency,
    PlanningPlan,
    PlanningRequest,
    PlanningSession,
    PlanningStep,
    PlanningValidationFinding,
    PlanningValidationResult,
)
from forge.autonomous_planning.policies import (
    AutonomousPlanningPolicy,
    PlanningLimits,
    PlanningQualityPolicy,
    PlanningSafetyPolicy,
)
from forge.autonomous_planning.states import (
    ApprovalRequirement,
    DependencyKind,
    PlanningIntent,
    PlanningRisk,
    PlanningState,
    StepKind,
)

__all__ = [
    "ApprovalRequirement",
    "AutonomousPlanningError",
    "AutonomousPlanningPolicy",
    "DependencyKind",
    "PlanningContractError",
    "PlanningDependency",
    "PlanningIntent",
    "PlanningLimits",
    "PlanningPlan",
    "PlanningPolicyError",
    "PlanningQualityPolicy",
    "PlanningRequest",
    "PlanningRisk",
    "PlanningSafetyPolicy",
    "PlanningScopeError",
    "PlanningSession",
    "PlanningState",
    "PlanningStateError",
    "PlanningStep",
    "PlanningValidationFinding",
    "PlanningValidationResult",
    "StepKind",
    "planning_dependency_identifier",
    "planning_plan_identifier",
    "planning_request_identifier",
    "planning_session_identifier",
    "planning_step_identifier",
]
'@

Write-Utf8NoBom "tests\test_autonomous_planning_identifiers.py" @'
from forge.autonomous_planning.identifiers import (
    planning_plan_identifier,
    planning_step_identifier,
)


def test_identifiers_are_deterministic() -> None:
    payload = {"objective": "Implement feature", "paths": {"b.py", "a.py"}}
    assert planning_plan_identifier(payload) == planning_plan_identifier(payload)


def test_identifier_prefixes_are_distinct() -> None:
    payload = {"name": "step"}
    assert planning_plan_identifier(payload).startswith("planning-plan-")
    assert planning_step_identifier(payload).startswith("planning-step-")
'@

Write-Utf8NoBom "tests\test_autonomous_planning_states.py" @'
from forge.autonomous_planning.states import (
    ApprovalRequirement,
    PlanningIntent,
    PlanningRisk,
    PlanningState,
    StepKind,
)


def test_state_values_are_stable() -> None:
    assert PlanningState.READY.value == "ready"
    assert PlanningIntent.FIX_DEFECT.value == "fix_defect"
    assert PlanningRisk.CRITICAL.value == "critical"
    assert StepKind.CODE_CHANGE.value == "code_change"
    assert ApprovalRequirement.PLAN.value == "plan"
'@

Write-Utf8NoBom "tests\test_autonomous_planning_policies.py" @'
from forge.autonomous_planning.policies import AutonomousPlanningPolicy


def test_default_policy_is_safe() -> None:
    policy = AutonomousPlanningPolicy()
    assert policy.safety.require_repository_scope
    assert policy.safety.require_validation_step
    assert not policy.safety.allow_destructive_steps
    assert policy.limits.maximum_steps == 50
'@

Write-Utf8NoBom "tests\test_autonomous_planning_models.py" @'
import pytest

from forge.autonomous_planning.errors import PlanningContractError
from forge.autonomous_planning.models import (
    PlanningDependency,
    PlanningPlan,
    PlanningRequest,
    PlanningStep,
    PlanningValidationFinding,
    PlanningValidationResult,
)
from forge.autonomous_planning.states import (
    ApprovalRequirement,
    DependencyKind,
    PlanningIntent,
    PlanningRisk,
    StepKind,
)


def step(step_id: str, sequence: int) -> PlanningStep:
    return PlanningStep(
        step_id=step_id,
        sequence=sequence,
        name=f"Step {sequence}",
        description="Perform a repository-grounded action.",
        kind=StepKind.ANALYSIS,
    )


def test_request_rejects_empty_objective() -> None:
    with pytest.raises(PlanningContractError):
        PlanningRequest(
            request_id="request-1",
            objective="",
            repository_root="repository",
            intent=PlanningIntent.INVESTIGATE,
            created_by="Aerion",
        )


def test_plan_accepts_ordered_steps() -> None:
    result = PlanningPlan(
        plan_id="plan-1",
        request_id="request-1",
        summary="Repository-grounded plan.",
        steps=(step("step-1", 1), step("step-2", 2)),
        dependencies=(
            PlanningDependency(
                dependency_id="dependency-1",
                source_step_id="step-2",
                target_step_id="step-1",
                kind=DependencyKind.REQUIRES,
                rationale="Step two requires step one.",
            ),
        ),
    )
    assert len(result.steps) == 2


def test_plan_rejects_unknown_dependency() -> None:
    with pytest.raises(PlanningContractError):
        PlanningPlan(
            plan_id="plan-1",
            request_id="request-1",
            summary="Invalid plan.",
            steps=(step("step-1", 1),),
            dependencies=(
                PlanningDependency(
                    dependency_id="dependency-1",
                    source_step_id="missing",
                    target_step_id="step-1",
                    kind=DependencyKind.REQUIRES,
                    rationale="Invalid reference.",
                ),
            ),
        )


def test_destructive_step_requires_approval() -> None:
    with pytest.raises(PlanningContractError):
        PlanningStep(
            step_id="step-1",
            sequence=1,
            name="Delete",
            description="Delete generated repository artifacts.",
            kind=StepKind.CODE_CHANGE,
            destructive=True,
            approval_requirement=ApprovalRequirement.NONE,
        )


def test_valid_result_rejects_blocking_finding() -> None:
    finding = PlanningValidationFinding(
        finding_id="finding-1",
        severity=PlanningRisk.HIGH,
        code="BLOCKED",
        message="Blocking issue.",
        blocking=True,
    )
    with pytest.raises(PlanningContractError):
        PlanningValidationResult(
            plan_id="plan-1",
            valid=True,
            findings=(finding,),
        )
'@

Write-Host ""
Write-Host "M5.6 Package 0 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check . --fix
Assert-Success "Ruff fix"

python -m ruff check .
Assert-Success "Ruff"

python -m mypy .
Assert-Success "MyPy"

python -m pytest `
    .\tests\test_autonomous_planning_identifiers.py `
    .\tests\test_autonomous_planning_states.py `
    .\tests\test_autonomous_planning_policies.py `
    .\tests\test_autonomous_planning_models.py `
    -p no:cacheprovider
Assert-Success "M5.6 Package 0 focused tests"

python -m pytest -p no:cacheprovider
Assert-Success "Full test suite"

Write-Host ""
Write-Host "M5.6 PACKAGE 0 COMPLETE" -ForegroundColor Green

git status --short
