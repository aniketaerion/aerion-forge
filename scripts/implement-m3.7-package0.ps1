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

Write-Utf8NoBom "forge\build_verification\errors.py" @'
"""Typed errors for M3.7 Build Verification."""


class BuildVerificationError(Exception):
    """Base error for build verification."""


class BuildVerificationConfigurationError(BuildVerificationError):
    """Raised when build verification configuration is invalid."""


class BuildVerificationPolicyError(BuildVerificationError):
    """Raised when a request violates a verification policy."""


class BuildVerificationValidationError(BuildVerificationError):
    """Raised when verification evidence is invalid."""


class BuildVerificationProviderError(BuildVerificationError):
    """Raised when a build provider cannot execute safely."""


class BuildVerificationTimeoutError(BuildVerificationProviderError):
    """Raised when a verification command exceeds its timeout."""


class BuildVerificationPersistenceError(BuildVerificationError):
    """Raised when verification evidence cannot be persisted."""


class BuildVerificationReportError(BuildVerificationError):
    """Raised when a verification report cannot be written."""


class BuildVerificationNotFoundError(BuildVerificationError):
    """Raised when requested verification evidence does not exist."""


class BuildVerificationStateError(BuildVerificationError):
    """Raised when the verification state transition is invalid."""
'@

Write-Utf8NoBom "forge\build_verification\identifiers.py" @'
"""Stable identifiers for M3.7 Build Verification."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any


def _normalize(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _normalize(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }

    if isinstance(value, Sequence) and not isinstance(
        value,
        (str, bytes, bytearray),
    ):
        return [_normalize(item) for item in value]

    if hasattr(value, "model_dump"):
        return _normalize(value.model_dump(mode="json"))

    if hasattr(value, "value"):
        return _normalize(value.value)

    return value


def stable_identifier(prefix: str, payload: Any) -> str:
    """Build a deterministic identifier from normalized JSON."""
    encoded = json.dumps(
        _normalize(payload),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")

    digest = hashlib.sha256(encoded).hexdigest()[:24]
    return f"{prefix}-{digest}"


def verification_request_identifier(payload: Any) -> str:
    return stable_identifier("build-request", payload)


def verification_step_identifier(payload: Any) -> str:
    return stable_identifier("build-step", payload)


def verification_run_identifier(payload: Any) -> str:
    return stable_identifier("build-run", payload)


def verification_evidence_identifier(payload: Any) -> str:
    return stable_identifier("build-evidence", payload)


def release_decision_identifier(payload: Any) -> str:
    return stable_identifier("release-decision", payload)
'@

Write-Utf8NoBom "forge\build_verification\models.py" @'
"""Immutable contracts for M3.7 Build Verification."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from pathlib import PurePosixPath

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class VerificationTool(StrEnum):
    RUFF = "ruff"
    MYPY = "mypy"
    PYTEST = "pytest"
    PYTHON_BUILD = "python_build"
    NODE_LINT = "node_lint"
    NODE_TEST = "node_test"
    NODE_BUILD = "node_build"
    CUSTOM = "custom"


class VerificationStatus(StrEnum):
    PLANNED = "planned"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"


class ReleaseDecision(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"
    MANUAL_REVIEW = "manual_review"


class FindingSeverity(StrEnum):
    INFORMATIONAL = "informational"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ImmutableModel(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        str_strip_whitespace=True,
    )


class VerificationStep(ImmutableModel):
    step_id: str = Field(min_length=1)
    tool: VerificationTool
    name: str = Field(min_length=1)
    arguments: tuple[str, ...] = ()
    working_directory: str = "."
    timeout_seconds: int = Field(default=300, ge=1, le=3600)
    required: bool = True
    allow_network: bool = False

    @field_validator("working_directory")
    @classmethod
    def validate_working_directory(cls, value: str) -> str:
        path = PurePosixPath(value.replace("\\", "/"))
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("working_directory must remain repository-relative")
        return path.as_posix()


class BuildVerificationRequest(ImmutableModel):
    request_id: str = Field(min_length=1)
    repository_root: str = Field(min_length=1)
    source_revision: str = Field(min_length=1)
    objective: str = Field(min_length=1)
    steps: tuple[VerificationStep, ...] = Field(min_length=1)
    target_paths: tuple[str, ...] = ()
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def validate_unique_steps(self) -> BuildVerificationRequest:
        step_ids = [step.step_id for step in self.steps]
        if len(step_ids) != len(set(step_ids)):
            raise ValueError("verification step identifiers must be unique")
        return self


class VerificationFinding(ImmutableModel):
    finding_id: str = Field(min_length=1)
    step_id: str = Field(min_length=1)
    severity: FindingSeverity
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    path: str | None = None
    line: int | None = Field(default=None, ge=1)
    column: int | None = Field(default=None, ge=1)


class VerificationStepResult(ImmutableModel):
    step_id: str = Field(min_length=1)
    status: VerificationStatus
    exit_code: int | None = None
    duration_seconds: float = Field(default=0.0, ge=0)
    stdout: tuple[str, ...] = ()
    stderr: tuple[str, ...] = ()
    findings: tuple[VerificationFinding, ...] = ()
    started_at: datetime | None = None
    completed_at: datetime | None = None

    @model_validator(mode="after")
    def validate_terminal_result(self) -> VerificationStepResult:
        terminal = {
            VerificationStatus.PASSED,
            VerificationStatus.FAILED,
            VerificationStatus.BLOCKED,
            VerificationStatus.TIMED_OUT,
            VerificationStatus.CANCELLED,
        }
        if self.status in terminal and self.completed_at is None:
            raise ValueError("terminal verification results require completed_at")
        return self


class BuildVerificationEvidence(ImmutableModel):
    evidence_id: str = Field(min_length=1)
    request: BuildVerificationRequest
    status: VerificationStatus
    step_results: tuple[VerificationStepResult, ...] = ()
    repository_fingerprint: str = Field(min_length=16)
    started_at: datetime
    completed_at: datetime | None = None

    @model_validator(mode="after")
    def validate_terminal_evidence(self) -> BuildVerificationEvidence:
        terminal = {
            VerificationStatus.PASSED,
            VerificationStatus.FAILED,
            VerificationStatus.BLOCKED,
            VerificationStatus.TIMED_OUT,
            VerificationStatus.CANCELLED,
        }
        if self.status in terminal and self.completed_at is None:
            raise ValueError("terminal verification evidence requires completed_at")
        return self


class ReleaseGateDecision(ImmutableModel):
    decision_id: str = Field(min_length=1)
    evidence_id: str = Field(min_length=1)
    decision: ReleaseDecision
    reasons: tuple[str, ...] = Field(min_length=1)
    blocking_findings: tuple[str, ...] = ()
    decided_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class BuildVerificationPolicy(ImmutableModel):
    allowed_tools: tuple[VerificationTool, ...] = (
        VerificationTool.RUFF,
        VerificationTool.MYPY,
        VerificationTool.PYTEST,
        VerificationTool.PYTHON_BUILD,
        VerificationTool.NODE_LINT,
        VerificationTool.NODE_TEST,
        VerificationTool.NODE_BUILD,
    )
    max_steps: int = Field(default=20, ge=1, le=100)
    max_timeout_seconds: int = Field(default=900, ge=1, le=3600)
    max_output_lines: int = Field(default=5000, ge=10, le=100000)
    allow_network: bool = False
    require_clean_working_tree: bool = True
    require_all_required_steps: bool = True
    reject_on_high_findings: bool = True
    reject_on_critical_findings: bool = True
'@

Write-Utf8NoBom "forge\build_verification\policies.py" @'
"""Policy enforcement for M3.7 Build Verification."""

from __future__ import annotations

from pathlib import Path

from forge.build_verification.errors import BuildVerificationPolicyError
from forge.build_verification.models import (
    BuildVerificationPolicy,
    BuildVerificationRequest,
    FindingSeverity,
    VerificationFinding,
)


def validate_request(
    request: BuildVerificationRequest,
    policy: BuildVerificationPolicy,
) -> None:
    if len(request.steps) > policy.max_steps:
        raise BuildVerificationPolicyError(
            f"request exceeds maximum step count: {policy.max_steps}"
        )

    for step in request.steps:
        if step.tool not in policy.allowed_tools:
            raise BuildVerificationPolicyError(
                f"verification tool is not allowed: {step.tool.value}"
            )
        if step.timeout_seconds > policy.max_timeout_seconds:
            raise BuildVerificationPolicyError(
                f"step timeout exceeds policy: {step.step_id}"
            )
        if step.allow_network and not policy.allow_network:
            raise BuildVerificationPolicyError(
                f"network access is not allowed: {step.step_id}"
            )


def resolve_repository_root(repository_root: str | Path) -> Path:
    root = Path(repository_root).expanduser().resolve()
    if not root.is_dir():
        raise BuildVerificationPolicyError(
            f"repository root does not exist: {root}"
        )
    if not (root / ".git").exists():
        raise BuildVerificationPolicyError(
            f"repository root is not a Git repository: {root}"
        )
    return root


def validate_target_paths(
    repository_root: Path,
    target_paths: tuple[str, ...],
) -> tuple[str, ...]:
    normalized: list[str] = []
    for raw_path in target_paths:
        candidate = (repository_root / raw_path).resolve()
        try:
            relative = candidate.relative_to(repository_root)
        except ValueError as exc:
            raise BuildVerificationPolicyError(
                f"target path escapes repository: {raw_path}"
            ) from exc
        normalized.append(relative.as_posix())
    return tuple(sorted(set(normalized)))


def blocking_finding_ids(
    findings: tuple[VerificationFinding, ...],
    policy: BuildVerificationPolicy,
) -> tuple[str, ...]:
    blocking: list[str] = []
    for finding in findings:
        if (
            finding.severity is FindingSeverity.CRITICAL
            and policy.reject_on_critical_findings
        ):
            blocking.append(finding.finding_id)
        elif (
            finding.severity is FindingSeverity.HIGH
            and policy.reject_on_high_findings
        ):
            blocking.append(finding.finding_id)
    return tuple(sorted(blocking))
'@

Write-Utf8NoBom "forge\build_verification\__init__.py" @'
"""M3.7 Build Verification public API."""

from forge.build_verification.errors import (
    BuildVerificationConfigurationError,
    BuildVerificationError,
    BuildVerificationNotFoundError,
    BuildVerificationPersistenceError,
    BuildVerificationPolicyError,
    BuildVerificationProviderError,
    BuildVerificationReportError,
    BuildVerificationStateError,
    BuildVerificationTimeoutError,
    BuildVerificationValidationError,
)
from forge.build_verification.identifiers import (
    release_decision_identifier,
    stable_identifier,
    verification_evidence_identifier,
    verification_request_identifier,
    verification_run_identifier,
    verification_step_identifier,
)
from forge.build_verification.models import (
    BuildVerificationEvidence,
    BuildVerificationPolicy,
    BuildVerificationRequest,
    FindingSeverity,
    ReleaseDecision,
    ReleaseGateDecision,
    VerificationFinding,
    VerificationStatus,
    VerificationStep,
    VerificationStepResult,
    VerificationTool,
)
from forge.build_verification.policies import (
    blocking_finding_ids,
    resolve_repository_root,
    validate_request,
    validate_target_paths,
)

__all__ = [
    "BuildVerificationConfigurationError",
    "BuildVerificationError",
    "BuildVerificationEvidence",
    "BuildVerificationNotFoundError",
    "BuildVerificationPersistenceError",
    "BuildVerificationPolicy",
    "BuildVerificationPolicyError",
    "BuildVerificationProviderError",
    "BuildVerificationReportError",
    "BuildVerificationRequest",
    "BuildVerificationStateError",
    "BuildVerificationTimeoutError",
    "BuildVerificationValidationError",
    "FindingSeverity",
    "ReleaseDecision",
    "ReleaseGateDecision",
    "VerificationFinding",
    "VerificationStatus",
    "VerificationStep",
    "VerificationStepResult",
    "VerificationTool",
    "blocking_finding_ids",
    "release_decision_identifier",
    "resolve_repository_root",
    "stable_identifier",
    "validate_request",
    "validate_target_paths",
    "verification_evidence_identifier",
    "verification_request_identifier",
    "verification_run_identifier",
    "verification_step_identifier",
]
'@

Write-Utf8NoBom "tests\test_build_verification_identifiers.py" @'
from forge.build_verification.identifiers import (
    release_decision_identifier,
    stable_identifier,
    verification_request_identifier,
)


def test_stable_identifier_is_deterministic() -> None:
    first = stable_identifier(
        "sample",
        {"paths": ["b.py", "a.py"], "revision": "abc"},
    )
    second = stable_identifier(
        "sample",
        {"revision": "abc", "paths": ["b.py", "a.py"]},
    )
    assert first == second
    assert first.startswith("sample-")


def test_request_identifier_changes_with_revision() -> None:
    first = verification_request_identifier(
        {"revision": "abc", "objective": "verify"}
    )
    second = verification_request_identifier(
        {"revision": "def", "objective": "verify"}
    )
    assert first != second


def test_release_decision_identifier_has_expected_prefix() -> None:
    identifier = release_decision_identifier(
        {"evidence_id": "evidence-1", "decision": "approved"}
    )
    assert identifier.startswith("release-decision-")
'@

Write-Utf8NoBom "tests\test_build_verification_models.py" @'
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from forge.build_verification.models import (
    BuildVerificationEvidence,
    BuildVerificationRequest,
    ReleaseDecision,
    ReleaseGateDecision,
    VerificationStatus,
    VerificationStep,
    VerificationStepResult,
    VerificationTool,
)


def test_step_rejects_repository_escape() -> None:
    with pytest.raises(ValidationError):
        VerificationStep(
            step_id="step-1",
            tool=VerificationTool.RUFF,
            name="Ruff",
            working_directory="../outside",
        )


def test_request_rejects_duplicate_step_ids() -> None:
    step = VerificationStep(
        step_id="step-1",
        tool=VerificationTool.RUFF,
        name="Ruff",
    )
    with pytest.raises(ValidationError):
        BuildVerificationRequest(
            request_id="request-1",
            repository_root=".",
            source_revision="abc",
            objective="verify",
            steps=(step, step),
        )


def test_terminal_step_result_requires_completion_time() -> None:
    with pytest.raises(ValidationError):
        VerificationStepResult(
            step_id="step-1",
            status=VerificationStatus.PASSED,
            exit_code=0,
        )


def test_terminal_evidence_requires_completion_time() -> None:
    step = VerificationStep(
        step_id="step-1",
        tool=VerificationTool.RUFF,
        name="Ruff",
    )
    request = BuildVerificationRequest(
        request_id="request-1",
        repository_root=".",
        source_revision="abc",
        objective="verify",
        steps=(step,),
    )
    with pytest.raises(ValidationError):
        BuildVerificationEvidence(
            evidence_id="evidence-1",
            request=request,
            status=VerificationStatus.PASSED,
            repository_fingerprint="a" * 64,
            started_at=datetime.now(UTC),
        )


def test_release_decision_requires_reason() -> None:
    with pytest.raises(ValidationError):
        ReleaseGateDecision(
            decision_id="decision-1",
            evidence_id="evidence-1",
            decision=ReleaseDecision.APPROVED,
            reasons=(),
        )
'@

Write-Utf8NoBom "tests\test_build_verification_policies.py" @'
from pathlib import Path

import pytest

from forge.build_verification.errors import BuildVerificationPolicyError
from forge.build_verification.models import (
    BuildVerificationPolicy,
    BuildVerificationRequest,
    FindingSeverity,
    VerificationFinding,
    VerificationStep,
    VerificationTool,
)
from forge.build_verification.policies import (
    blocking_finding_ids,
    validate_request,
    validate_target_paths,
)


def test_policy_rejects_network_step() -> None:
    step = VerificationStep(
        step_id="step-1",
        tool=VerificationTool.PYTEST,
        name="Pytest",
        allow_network=True,
    )
    request = BuildVerificationRequest(
        request_id="request-1",
        repository_root=".",
        source_revision="abc",
        objective="verify",
        steps=(step,),
    )
    with pytest.raises(BuildVerificationPolicyError):
        validate_request(request, BuildVerificationPolicy())


def test_target_paths_are_normalized(tmp_path: Path) -> None:
    (tmp_path / "forge").mkdir()
    normalized = validate_target_paths(tmp_path, ("forge", "forge"))
    assert normalized == ("forge",)


def test_high_finding_blocks_release() -> None:
    finding = VerificationFinding(
        finding_id="finding-1",
        step_id="step-1",
        severity=FindingSeverity.HIGH,
        code="TEST",
        message="blocking issue",
    )
    assert blocking_finding_ids(
        (finding,),
        BuildVerificationPolicy(),
    ) == ("finding-1",)
'@

Write-Utf8NoBom "docs\build_verification\ARCHITECTURE.md" @'
# M3.7 Build Verification Architecture

M3.7 adds a deterministic release-verification boundary after mission execution.
It accepts a bounded verification request, executes registered providers,
normalizes evidence, and produces a release-gate decision.

The subsystem does not merge branches, publish packages, deploy services, or
modify source files.
'@

Write-Utf8NoBom "docs\build_verification\SPECIFICATION.md" @'
# M3.7 Build Verification Specification

The subsystem shall verify one immutable repository revision, execute only
allow-listed providers, deny network access by default, capture complete
evidence, and produce a deterministic release decision.
'@

Write-Utf8NoBom "docs\build_verification\DATA_MODEL.md" @'
# M3.7 Build Verification Data Model

Primary immutable contracts are `VerificationStep`,
`BuildVerificationRequest`, `VerificationFinding`,
`VerificationStepResult`, `BuildVerificationEvidence`,
`ReleaseGateDecision`, and `BuildVerificationPolicy`.
'@

Write-Utf8NoBom "docs\build_verification\SECURITY_MODEL.md" @'
# M3.7 Build Verification Security Model

The subsystem is fail-closed. Commands come from registered providers, network
access is denied by default, paths remain repository-relative, timeouts and
outputs are bounded, and no automatic deployment or merge is permitted.
'@

Write-Utf8NoBom "docs\build_verification\RELEASE_GATE.md" @'
# M3.7 Release Gate

Release approval requires all required steps to pass, complete evidence, no
policy-defined blocking finding, matching repository evidence, and satisfaction
of the configured working-tree requirement.
'@

Write-Utf8NoBom "docs\build_verification\STATE_MACHINE.md" @'
# M3.7 Build Verification State Machine

`planned -> running -> passed`

Failure paths are `failed`, `blocked`, `timed_out`, and `cancelled`.
Release outcomes are `approved`, `rejected`, and `manual_review`.
'@

Write-Utf8NoBom "docs\build_verification\ACCEPTANCE_CRITERIA.md" @'
# M3.7 Package 0 Acceptance Criteria

Package 0 is accepted when contracts are immutable, identifiers are stable,
path escape is rejected, network access is denied by default, policy limits are
enforced, documentation is complete, and all quality gates pass.
'@

Write-Host ""
Write-Host "M3.7 Package 0 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_build_verification_identifiers.py `
    .\tests\test_build_verification_models.py `
    .\tests\test_build_verification_policies.py `
    -p no:cacheprovider
Assert-CommandSuccess "M3.7 Package 0 tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M3.7 PACKAGE 0 COMPLETE" -ForegroundColor Green

git status --short