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

Write-Utf8NoBom "forge\domain_intelligence\phase_validation\errors.py" @'
"""Typed errors for M4.8 Phase Validation Intelligence."""

from __future__ import annotations

from forge.domain_intelligence.errors import DomainIntelligenceError


class PhaseValidationError(DomainIntelligenceError):
    """Base error for phase-validation intelligence."""


class PhaseValidationConfigurationError(PhaseValidationError):
    """Raised when validation configuration is invalid."""


class PhaseValidationPolicyError(PhaseValidationError):
    """Raised when validation policy is violated."""


class PhaseValidationExecutionError(PhaseValidationError):
    """Raised when a validation check cannot execute."""


class PhaseReleaseError(PhaseValidationError):
    """Raised when a phase is not eligible for release."""
'@

Write-Utf8NoBom "forge\domain_intelligence\phase_validation\identifiers.py" @'
"""Deterministic identifiers for M4.8 Phase Validation Intelligence."""

from __future__ import annotations

from typing import Any

from forge.domain_intelligence.identifiers import stable_identifier


def phase_validation_check_identifier(payload: Any) -> str:
    return stable_identifier("phase-validation-check", payload)


def phase_validation_result_identifier(payload: Any) -> str:
    return stable_identifier("phase-validation-result", payload)


def phase_validation_finding_identifier(payload: Any) -> str:
    return stable_identifier("phase-validation-finding", payload)


def phase_validation_report_identifier(payload: Any) -> str:
    return stable_identifier("phase-validation-report", payload)


def phase_release_manifest_identifier(payload: Any) -> str:
    return stable_identifier("phase-release-manifest", payload)
'@

Write-Utf8NoBom "forge\domain_intelligence\phase_validation\models.py" @'
"""Immutable contracts for M4.8 Phase Validation Intelligence."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PhaseValidationKind(StrEnum):
    ARCHITECTURE = "architecture"
    ACCEPTANCE = "acceptance"
    COVERAGE = "coverage"
    COMPATIBILITY = "compatibility"
    RELEASE = "release"
    SECURITY = "security"
    QUALITY = "quality"
    UNKNOWN = "unknown"


class PhaseValidationStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"
    SKIP = "skip"
    ERROR = "error"


class PhaseFindingSeverity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ImmutablePhaseValidationModel(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        str_strip_whitespace=True,
    )


class PhaseValidationRequest(ImmutablePhaseValidationModel):
    repository_root: str = Field(min_length=1)
    phase: str = Field(min_length=1)
    milestone: str | None = None
    require_clean_worktree: bool = True
    require_release_tag: bool = False
    minimum_test_count: int = Field(default=1, ge=0)
    minimum_coverage_percent: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
    )


class PhaseValidationCheck(ImmutablePhaseValidationModel):
    check_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    kind: PhaseValidationKind
    required: bool = True
    description: str = Field(default="", max_length=2000)


class PhaseValidationResult(ImmutablePhaseValidationModel):
    result_id: str = Field(min_length=1)
    check_id: str = Field(min_length=1)
    status: PhaseValidationStatus
    message: str = Field(min_length=1)
    evidence: dict[str, str] = Field(default_factory=dict)
    duration_seconds: float = Field(default=0.0, ge=0.0)


class PhaseValidationFinding(ImmutablePhaseValidationModel):
    finding_id: str = Field(min_length=1)
    category: str = Field(min_length=1)
    severity: PhaseFindingSeverity
    message: str = Field(min_length=1)
    path: str | None = None
    evidence: dict[str, str] = Field(default_factory=dict)


class PhaseReleaseManifest(ImmutablePhaseValidationModel):
    manifest_id: str = Field(min_length=1)
    phase: str = Field(min_length=1)
    milestone: str | None = None
    commit: str = Field(min_length=1)
    branch: str = Field(min_length=1)
    tag: str | None = None
    validation_result_ids: tuple[str, ...] = ()
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )

    @field_validator("validation_result_ids")
    @classmethod
    def ensure_unique_result_ids(
        cls,
        result_ids: tuple[str, ...],
    ) -> tuple[str, ...]:
        if len(result_ids) != len(set(result_ids)):
            raise ValueError(
                "validation result identifiers must be unique"
            )
        return result_ids


class PhaseValidationReport(ImmutablePhaseValidationModel):
    report_id: str = Field(min_length=1)
    phase: str = Field(min_length=1)
    milestone: str | None = None
    checks: tuple[PhaseValidationCheck, ...] = ()
    results: tuple[PhaseValidationResult, ...] = ()
    findings: tuple[PhaseValidationFinding, ...] = ()
    release_manifest: PhaseReleaseManifest | None = None
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )

    @field_validator("checks")
    @classmethod
    def ensure_unique_checks(
        cls,
        checks: tuple[PhaseValidationCheck, ...],
    ) -> tuple[PhaseValidationCheck, ...]:
        identifiers = [check.check_id for check in checks]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("validation check identifiers must be unique")
        return checks

    @field_validator("results")
    @classmethod
    def ensure_unique_results(
        cls,
        results: tuple[PhaseValidationResult, ...],
    ) -> tuple[PhaseValidationResult, ...]:
        identifiers = [result.result_id for result in results]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("validation result identifiers must be unique")
        return results

    @property
    def passed(self) -> bool:
        required_ids = {
            check.check_id
            for check in self.checks
            if check.required
        }
        required_results = {
            result.check_id: result
            for result in self.results
            if result.check_id in required_ids
        }

        return bool(required_ids) and all(
            required_results.get(check_id) is not None
            and required_results[check_id].status
            is PhaseValidationStatus.PASS
            for check_id in required_ids
        )
'@

Write-Utf8NoBom "forge\domain_intelligence\phase_validation\policies.py" @'
"""Policies for M4.8 Phase Validation Intelligence."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from forge.domain_intelligence.phase_validation.errors import (
    PhaseValidationPolicyError,
)
from forge.domain_intelligence.phase_validation.models import (
    PhaseValidationRequest,
)


class PhaseValidationPolicy(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    allow_network: bool = False
    allow_repository_mutation: bool = False
    allow_destructive_commands: bool = False
    require_git_repository: bool = True
    require_clean_worktree: bool = True
    maximum_validation_seconds: int = Field(
        default=900,
        ge=1,
        le=7200,
    )
    minimum_test_count: int = Field(default=1, ge=0)
    minimum_coverage_percent: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
    )


def resolve_phase_repository_root(
    repository_root: str | Path,
    policy: PhaseValidationPolicy,
) -> Path:
    root = Path(repository_root).expanduser().resolve()

    if not root.is_dir():
        raise PhaseValidationPolicyError(
            f"repository root does not exist: {root}"
        )

    if policy.require_git_repository and not (root / ".git").exists():
        raise PhaseValidationPolicyError(
            f"repository root is not a Git repository: {root}"
        )

    return root


def validate_phase_request(
    request: PhaseValidationRequest,
    policy: PhaseValidationPolicy,
) -> None:
    if not request.phase.strip():
        raise PhaseValidationPolicyError("phase must not be empty")

    if request.minimum_test_count < policy.minimum_test_count:
        raise PhaseValidationPolicyError(
            "requested minimum test count is below policy minimum"
        )

    if (
        request.minimum_coverage_percent
        < policy.minimum_coverage_percent
    ):
        raise PhaseValidationPolicyError(
            "requested coverage threshold is below policy minimum"
        )

    if (
        policy.require_clean_worktree
        and not request.require_clean_worktree
    ):
        raise PhaseValidationPolicyError(
            "clean working tree validation cannot be disabled"
        )
'@

Write-Utf8NoBom "forge\domain_intelligence\phase_validation\__init__.py" @'
"""M4.8 Phase Validation Intelligence public API."""

from forge.domain_intelligence.phase_validation.errors import (
    PhaseReleaseError,
    PhaseValidationConfigurationError,
    PhaseValidationError,
    PhaseValidationExecutionError,
    PhaseValidationPolicyError,
)
from forge.domain_intelligence.phase_validation.identifiers import (
    phase_release_manifest_identifier,
    phase_validation_check_identifier,
    phase_validation_finding_identifier,
    phase_validation_report_identifier,
    phase_validation_result_identifier,
)
from forge.domain_intelligence.phase_validation.models import (
    PhaseFindingSeverity,
    PhaseReleaseManifest,
    PhaseValidationCheck,
    PhaseValidationFinding,
    PhaseValidationKind,
    PhaseValidationReport,
    PhaseValidationRequest,
    PhaseValidationResult,
    PhaseValidationStatus,
)
from forge.domain_intelligence.phase_validation.policies import (
    PhaseValidationPolicy,
    resolve_phase_repository_root,
    validate_phase_request,
)

__all__ = [
    "PhaseFindingSeverity",
    "PhaseReleaseError",
    "PhaseReleaseManifest",
    "PhaseValidationCheck",
    "PhaseValidationConfigurationError",
    "PhaseValidationError",
    "PhaseValidationExecutionError",
    "PhaseValidationFinding",
    "PhaseValidationKind",
    "PhaseValidationPolicy",
    "PhaseValidationPolicyError",
    "PhaseValidationReport",
    "PhaseValidationRequest",
    "PhaseValidationResult",
    "PhaseValidationStatus",
    "phase_release_manifest_identifier",
    "phase_validation_check_identifier",
    "phase_validation_finding_identifier",
    "phase_validation_report_identifier",
    "phase_validation_result_identifier",
    "resolve_phase_repository_root",
    "validate_phase_request",
]
'@

Write-Utf8NoBom "tests\test_domain_intelligence_phase_validation_identifiers.py" @'
from forge.domain_intelligence.phase_validation.identifiers import (
    phase_validation_check_identifier,
    phase_validation_result_identifier,
)


def test_phase_validation_check_identifier_is_deterministic() -> None:
    first = phase_validation_check_identifier(
        {"phase": "4", "name": "architecture"}
    )
    second = phase_validation_check_identifier(
        {"name": "architecture", "phase": "4"}
    )

    assert first == second
    assert first.startswith("phase-validation-check-")


def test_phase_validation_result_identifier_changes_by_status() -> None:
    passed = phase_validation_result_identifier(
        {"check_id": "check-1", "status": "pass"}
    )
    failed = phase_validation_result_identifier(
        {"check_id": "check-1", "status": "fail"}
    )

    assert passed != failed
'@

Write-Utf8NoBom "tests\test_domain_intelligence_phase_validation_models.py" @'
import pytest
from pydantic import ValidationError

from forge.domain_intelligence.phase_validation.models import (
    PhaseValidationCheck,
    PhaseValidationKind,
    PhaseValidationReport,
    PhaseValidationResult,
    PhaseValidationStatus,
)


def test_phase_validation_models_are_immutable() -> None:
    check = PhaseValidationCheck(
        check_id="check-1",
        name="Architecture",
        kind=PhaseValidationKind.ARCHITECTURE,
    )

    with pytest.raises(ValidationError):
        check.name = "Changed"


def test_phase_validation_report_requires_unique_checks() -> None:
    check = PhaseValidationCheck(
        check_id="check-1",
        name="Architecture",
        kind=PhaseValidationKind.ARCHITECTURE,
    )

    with pytest.raises(ValidationError):
        PhaseValidationReport(
            report_id="report-1",
            phase="4",
            checks=(check, check),
        )


def test_phase_validation_report_passed_property() -> None:
    check = PhaseValidationCheck(
        check_id="check-1",
        name="Architecture",
        kind=PhaseValidationKind.ARCHITECTURE,
    )
    result = PhaseValidationResult(
        result_id="result-1",
        check_id=check.check_id,
        status=PhaseValidationStatus.PASS,
        message="Architecture validation passed.",
    )

    report = PhaseValidationReport(
        report_id="report-1",
        phase="4",
        checks=(check,),
        results=(result,),
    )

    assert report.passed
'@

Write-Utf8NoBom "tests\test_domain_intelligence_phase_validation_policies.py" @'
from pathlib import Path

import pytest

from forge.domain_intelligence.phase_validation.errors import (
    PhaseValidationPolicyError,
)
from forge.domain_intelligence.phase_validation.models import (
    PhaseValidationRequest,
)
from forge.domain_intelligence.phase_validation.policies import (
    PhaseValidationPolicy,
    resolve_phase_repository_root,
    validate_phase_request,
)


def test_phase_validation_policy_is_offline_read_only() -> None:
    policy = PhaseValidationPolicy()

    assert not policy.allow_network
    assert not policy.allow_repository_mutation
    assert not policy.allow_destructive_commands


def test_phase_repository_requires_git(tmp_path: Path) -> None:
    with pytest.raises(PhaseValidationPolicyError):
        resolve_phase_repository_root(
            tmp_path,
            PhaseValidationPolicy(),
        )


def test_phase_request_cannot_disable_clean_worktree() -> None:
    request = PhaseValidationRequest(
        repository_root=".",
        phase="4",
        require_clean_worktree=False,
    )

    with pytest.raises(PhaseValidationPolicyError):
        validate_phase_request(
            request,
            PhaseValidationPolicy(),
        )
'@

Write-Utf8NoBom "docs\domain_intelligence\phase_validation\ARCHITECTURE.md" @'
# M4.8 Phase Validation Intelligence Architecture

M4.8 provides deterministic phase and milestone validation across
architecture, acceptance criteria, coverage, compatibility, security,
quality, and release readiness.

Package 0 establishes immutable contracts, deterministic identifiers,
typed errors, release-manifest models, and offline read-only policy
boundaries.
'@

Write-Utf8NoBom "docs\domain_intelligence\phase_validation\SPECIFICATION.md" @'
# M4.8 Phase Validation Intelligence Specification

The subsystem shall discover validation requirements, execute checks,
aggregate results and findings, assess release eligibility, generate
reports, and produce deterministic release manifests without modifying
the repository or using network access.
'@

Write-Utf8NoBom "docs\domain_intelligence\phase_validation\DATA_MODEL.md" @'
# M4.8 Phase Validation Intelligence Data Model

Core models:

- `PhaseValidationRequest`
- `PhaseValidationCheck`
- `PhaseValidationResult`
- `PhaseValidationFinding`
- `PhaseValidationReport`
- `PhaseReleaseManifest`

All models are immutable and reject unknown fields.
'@

Write-Utf8NoBom "docs\domain_intelligence\phase_validation\SECURITY_MODEL.md" @'
# M4.8 Phase Validation Intelligence Security Model

Validation is offline and read-only.

The policy prohibits network access, repository mutation, destructive
commands, invalid repository roots, disabling clean-worktree validation,
and thresholds weaker than the configured policy baseline.
'@

Write-Utf8NoBom "docs\domain_intelligence\phase_validation\ACCEPTANCE_CRITERIA.md" @'
# M4.8 Package 0 Acceptance Criteria

- Typed phase-validation errors exist.
- Stable identifiers are deterministic.
- Models are immutable and validated.
- Duplicate check and result identifiers are rejected.
- Release-manifest contracts exist.
- Policies prohibit network access and mutation.
- Git repository and clean-worktree requirements are enforceable.
- Ruff, MyPy, focused tests, and the full test suite pass.
'@

Write-Host ""
Write-Host "M4.8 Package 0 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check . --fix
Assert-CommandSuccess "Ruff fix"

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_domain_intelligence_phase_validation_identifiers.py `
    .\tests\test_domain_intelligence_phase_validation_models.py `
    .\tests\test_domain_intelligence_phase_validation_policies.py `
    -p no:cacheprovider
Assert-CommandSuccess "M4.8 Package 0 tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M4.8 PACKAGE 0 COMPLETE" -ForegroundColor Green

git status --short
