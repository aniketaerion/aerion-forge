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

Write-Utf8NoBom "forge\validation_repair\errors.py" @'
"""Typed errors for validation and repair orchestration."""


class ValidationRepairError(RuntimeError):
    """Base error for validation and repair."""


class InvalidValidationCommandError(ValidationRepairError):
    """Raised when a validation command is not permitted."""


class ValidationExecutionError(ValidationRepairError):
    """Raised when validation execution fails unexpectedly."""


class ValidationTimeoutError(ValidationRepairError):
    """Raised when a validation command exceeds its timeout."""


class ValidationOutputParseError(ValidationRepairError):
    """Raised when validation output cannot be interpreted."""


class RepairPlanningError(ValidationRepairError):
    """Raised when a bounded repair candidate cannot be planned."""


class RepairApprovalRequiredError(ValidationRepairError):
    """Raised when repair application lacks explicit approval."""


class RepairAttemptLimitError(ValidationRepairError):
    """Raised when the configured attempt limit is exhausted."""


class RepairStateChangedError(ValidationRepairError):
    """Raised when repository state changes unexpectedly."""


class RepairExecutionError(ValidationRepairError):
    """Raised when a repair cannot be executed safely."""


class RepairRollbackError(ValidationRepairError):
    """Raised when rollback cannot restore the prior state."""
'@

Write-Utf8NoBom "forge\validation_repair\identifiers.py" @'
"""Deterministic identifiers for validation and repair."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any


def sha256_text(value: str) -> str:
    """Return a SHA-256 digest for UTF-8 text."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def stable_identifier(
    prefix: str,
    payload: Mapping[str, Any] | Sequence[Any] | str,
) -> str:
    """Build a stable identifier from canonical JSON."""
    if isinstance(payload, str):
        canonical = payload
    else:
        canonical = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            default=str,
        )
    return f"{prefix}_{sha256_text(canonical)[:24]}"


def validation_run_identifier(payload: Mapping[str, Any]) -> str:
    """Return a stable validation-run identifier."""
    return stable_identifier("valrun", payload)


def repair_candidate_identifier(payload: Mapping[str, Any]) -> str:
    """Return a stable repair-candidate identifier."""
    return stable_identifier("repair", payload)


def repair_session_identifier(payload: Mapping[str, Any]) -> str:
    """Return a stable repair-session identifier."""
    return stable_identifier("repsess", payload)
'@

Write-Utf8NoBom "forge\validation_repair\models.py" @'
"""Immutable contracts for M3.4 Validation and Repair."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FrozenModel(BaseModel):
    """Base class for immutable contracts."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class ValidationTool(StrEnum):
    """Supported validation tools."""

    RUFF = "ruff"
    MYPY = "mypy"
    PYTEST = "pytest"


class ValidationStatus(StrEnum):
    """Validation execution status."""

    PASSED = "passed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    ERROR = "error"


class FindingSeverity(StrEnum):
    """Normalized validation-finding severity."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class RepairStatus(StrEnum):
    """Repair attempt state."""

    PLANNED = "planned"
    DRY_RUN = "dry_run"
    APPLIED = "applied"
    VALIDATED = "validated"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class ValidationCommand(FrozenModel):
    """One permitted validation command."""

    command_id: str
    tool: ValidationTool
    arguments: tuple[str, ...] = ()
    timeout_seconds: Annotated[int, Field(gt=0)] = 300
    target_paths: tuple[str, ...] = ()


class ValidationFinding(FrozenModel):
    """One normalized finding from a validation tool."""

    finding_id: str
    tool: ValidationTool
    severity: FindingSeverity
    code: str
    message: str
    path: str | None = None
    line: int | None = Field(default=None, ge=1)
    column: int | None = Field(default=None, ge=1)


class ValidationRun(FrozenModel):
    """Complete result for one validation command."""

    run_id: str
    command: ValidationCommand
    status: ValidationStatus
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    duration_seconds: float = Field(ge=0)
    findings: tuple[ValidationFinding, ...] = ()


class RepairCandidate(FrozenModel):
    """One bounded candidate repair."""

    candidate_id: str
    finding_ids: tuple[str, ...]
    objective: str
    target_paths: tuple[str, ...]
    change_plan_id: str | None = None
    risk_notes: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_candidate(self) -> RepairCandidate:
        if not self.finding_ids:
            raise ValueError("repair candidate requires at least one finding")
        if not self.target_paths:
            raise ValueError("repair candidate requires at least one target path")
        return self


class RepairAttempt(FrozenModel):
    """One dry-run or applied repair attempt."""

    attempt_number: Annotated[int, Field(ge=1)]
    candidate: RepairCandidate
    status: RepairStatus
    safe_edit_request_id: str | None = None
    validation_runs: tuple[ValidationRun, ...] = ()
    errors: tuple[str, ...] = ()


class RepairSession(FrozenModel):
    """Bounded repair session."""

    session_id: str
    repository_root: str
    max_attempts: Annotated[int, Field(ge=1)]
    attempts: tuple[RepairAttempt, ...] = ()
    approved: bool = False

    @model_validator(mode="after")
    def validate_attempt_count(self) -> RepairSession:
        if len(self.attempts) > self.max_attempts:
            raise ValueError("attempt count exceeds configured maximum")
        return self


class RepairReport(FrozenModel):
    """Final repair-session evidence."""

    session_id: str
    repository_root: str
    succeeded: bool
    attempts: tuple[RepairAttempt, ...]
    final_validation_runs: tuple[ValidationRun, ...] = ()
    messages: tuple[str, ...] = ()
'@

Write-Utf8NoBom "forge\validation_repair\policies.py" @'
"""Safety policy for validation and repair."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field

from forge.validation_repair.errors import (
    InvalidValidationCommandError,
    RepairApprovalRequiredError,
)
from forge.validation_repair.models import FrozenModel, ValidationCommand, ValidationTool


class ValidationRepairPolicy(FrozenModel):
    """Immutable policy for bounded validation and repair."""

    max_repair_attempts: int = Field(default=3, ge=1, le=10)
    default_timeout_seconds: int = Field(default=300, gt=0)
    allowed_tools: tuple[ValidationTool, ...] = (
        ValidationTool.RUFF,
        ValidationTool.MYPY,
        ValidationTool.PYTEST,
    )
    require_explicit_approval: bool = True
    dry_run_default: bool = True
    rollback_failed_repairs: bool = True
    stop_on_repository_state_change: bool = True
    allow_shell: bool = False

    def validate_command(self, command: ValidationCommand) -> None:
        """Reject unsupported tools and unsafe argument forms."""
        if command.tool not in self.allowed_tools:
            raise InvalidValidationCommandError(
                f"validation tool is not permitted: {command.tool}"
            )

        forbidden_tokens = {";", "&&", "||", "|", ">", "<"}
        if any(token in argument for argument in command.arguments for token in forbidden_tokens):
            raise InvalidValidationCommandError(
                "shell metacharacters are not permitted in validation arguments"
            )

    def validate_apply_mode(self, *, dry_run: bool, approved: bool) -> None:
        """Require explicit approval for applied repairs."""
        if not dry_run and self.require_explicit_approval and not approved:
            raise RepairApprovalRequiredError(
                "repair application requires explicit approval"
            )

    @staticmethod
    def resolve_repository(repository_root: Path) -> Path:
        """Resolve and validate the repository root."""
        root = repository_root.expanduser().resolve()
        if not root.is_dir():
            raise ValueError(f"repository root does not exist: {root}")
        return root
'@

Write-Utf8NoBom "forge\validation_repair\__init__.py" @'
"""M3.4 Validation and Repair contracts."""

from forge.validation_repair.identifiers import (
    repair_candidate_identifier,
    repair_session_identifier,
    sha256_text,
    stable_identifier,
    validation_run_identifier,
)
from forge.validation_repair.models import (
    FindingSeverity,
    RepairAttempt,
    RepairCandidate,
    RepairReport,
    RepairSession,
    RepairStatus,
    ValidationCommand,
    ValidationFinding,
    ValidationRun,
    ValidationStatus,
    ValidationTool,
)
from forge.validation_repair.policies import ValidationRepairPolicy

__all__ = [
    "FindingSeverity",
    "RepairAttempt",
    "RepairCandidate",
    "RepairReport",
    "RepairSession",
    "RepairStatus",
    "ValidationCommand",
    "ValidationFinding",
    "ValidationRepairPolicy",
    "ValidationRun",
    "ValidationStatus",
    "ValidationTool",
    "repair_candidate_identifier",
    "repair_session_identifier",
    "sha256_text",
    "stable_identifier",
    "validation_run_identifier",
]
'@

Write-Utf8NoBom "tests\test_validation_repair_identifiers.py" @'
from forge.validation_repair.identifiers import (
    repair_candidate_identifier,
    stable_identifier,
    validation_run_identifier,
)


def test_stable_identifier_is_deterministic() -> None:
    assert stable_identifier("x", {"a": 1, "b": 2}) == stable_identifier(
        "x", {"b": 2, "a": 1}
    )


def test_validation_run_identifier_prefix() -> None:
    assert validation_run_identifier({"tool": "ruff"}).startswith("valrun_")


def test_repair_candidate_identifier_changes_with_payload() -> None:
    assert repair_candidate_identifier({"x": 1}) != repair_candidate_identifier({"x": 2})
'@

Write-Utf8NoBom "tests\test_validation_repair_models.py" @'
import pytest
from pydantic import ValidationError

from forge.validation_repair.models import (
    FindingSeverity,
    RepairCandidate,
    RepairSession,
    ValidationCommand,
    ValidationFinding,
    ValidationTool,
)


def test_validation_command_is_immutable() -> None:
    command = ValidationCommand(
        command_id="cmd-1",
        tool=ValidationTool.RUFF,
    )

    with pytest.raises(ValidationError):
        command.timeout_seconds = 10


def test_finding_rejects_invalid_line_number() -> None:
    with pytest.raises(ValidationError):
        ValidationFinding(
            finding_id="finding-1",
            tool=ValidationTool.MYPY,
            severity=FindingSeverity.ERROR,
            code="assignment",
            message="invalid assignment",
            line=0,
        )


def test_repair_candidate_requires_findings_and_targets() -> None:
    with pytest.raises(ValidationError):
        RepairCandidate(
            candidate_id="repair-1",
            finding_ids=(),
            objective="repair failure",
            target_paths=(),
        )


def test_repair_session_rejects_excess_attempts() -> None:
    with pytest.raises(ValidationError):
        RepairSession(
            session_id="session-1",
            repository_root=".",
            max_attempts=1,
            attempts=(
                {
                    "attempt_number": 1,
                    "candidate": {
                        "candidate_id": "r1",
                        "finding_ids": ["f1"],
                        "objective": "fix",
                        "target_paths": ["a.py"],
                    },
                    "status": "planned",
                },
                {
                    "attempt_number": 2,
                    "candidate": {
                        "candidate_id": "r2",
                        "finding_ids": ["f2"],
                        "objective": "fix",
                        "target_paths": ["b.py"],
                    },
                    "status": "planned",
                },
            ),
        )
'@

Write-Utf8NoBom "tests\test_validation_repair_policies.py" @'
from pathlib import Path

import pytest

from forge.validation_repair.errors import (
    InvalidValidationCommandError,
    RepairApprovalRequiredError,
)
from forge.validation_repair.models import ValidationCommand, ValidationTool
from forge.validation_repair.policies import ValidationRepairPolicy


def test_policy_defaults_are_bounded() -> None:
    policy = ValidationRepairPolicy()

    assert policy.max_repair_attempts == 3
    assert policy.dry_run_default is True
    assert policy.allow_shell is False


def test_policy_rejects_shell_metacharacters() -> None:
    command = ValidationCommand(
        command_id="cmd-1",
        tool=ValidationTool.PYTEST,
        arguments=("tests", "&&", "whoami"),
    )

    with pytest.raises(InvalidValidationCommandError):
        ValidationRepairPolicy().validate_command(command)


def test_policy_requires_approval_for_apply() -> None:
    with pytest.raises(RepairApprovalRequiredError):
        ValidationRepairPolicy().validate_apply_mode(
            dry_run=False,
            approved=False,
        )


def test_policy_resolves_existing_repository(tmp_path: Path) -> None:
    assert ValidationRepairPolicy.resolve_repository(tmp_path) == tmp_path.resolve()
'@

Write-Utf8NoBom "docs\validation_repair\ARCHITECTURE.md" @'
# M3.4 Validation and Repair Architecture

## Objective

Turn M3.3 safe edits into a bounded engineering loop that validates changes, interprets failures, plans candidate repairs and revalidates until success or an attempt limit is reached.

## Components

1. Contracts and identifiers.
2. Validation runner.
3. Output parser.
4. Repair planner.
5. Repair service.
6. CLI and release validation.

## Flow

Safe edit → targeted validation → normalized findings → bounded repair candidate → approved repair → revalidation → success or stop.

## Safety boundary

M3.4 does not allow unrestricted shell execution, unbounded retries, silent approval, autonomous Git commits or uncontrolled repository mutation.
'@

Write-Utf8NoBom "docs\validation_repair\SPECIFICATION.md" @'
# M3.4 Validation and Repair Specification

Supported validation tools are Ruff, MyPy and Pytest.

Every execution captures:

- command identity;
- tool and arguments;
- timeout;
- exit code;
- standard output;
- standard error;
- duration;
- normalized findings.

Repair execution must use M3.2 planning and M3.3 safe editing. Applied repairs require explicit approval and unsuccessful attempts must be rolled back when policy requires it.
'@

Write-Utf8NoBom "docs\validation_repair\DATA_MODEL.md" @'
# M3.4 Data Model

Core immutable contracts:

- `ValidationCommand`
- `ValidationFinding`
- `ValidationRun`
- `RepairCandidate`
- `RepairAttempt`
- `RepairSession`
- `RepairReport`

A repair session is bounded by `max_attempts`. Every attempt records its candidate, state, validation runs and errors.
'@

Write-Utf8NoBom "docs\validation_repair\OPERATIONS.md" @'
# M3.4 Operations

## Dry run

1. Validate command policy.
2. Run approved validation tools.
3. Parse findings.
4. Produce repair candidates.
5. Do not modify files.

## Apply

1. Require explicit approval.
2. Verify repository state.
3. Execute repair through Safe Code Editing.
4. Re-run targeted validation.
5. Roll back unsuccessful repair attempts.
6. Stop on success or configured attempt limit.
'@

Write-Utf8NoBom "docs\validation_repair\ACCEPTANCE_CRITERIA.md" @'
# M3.4 Acceptance Criteria

M3.4 is complete when:

- Ruff, MyPy and Pytest commands are represented by immutable contracts;
- unsupported tools and shell metacharacters are rejected;
- timeouts are enforced;
- outputs are normalized into structured findings;
- repair candidates are bounded to explicit paths and findings;
- apply mode requires explicit approval;
- repair attempts cannot exceed policy limits;
- repository state changes stop execution;
- failed repair attempts roll back;
- final reports contain complete evidence;
- full project quality gates and M3.4 validation scripts pass.
'@

Write-Host ""
Write-Host "Package 0 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m mypy .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m pytest `
    .\tests\test_validation_repair_identifiers.py `
    .\tests\test_validation_repair_models.py `
    .\tests\test_validation_repair_policies.py `
    -p no:cacheprovider
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m pytest -p no:cacheprovider
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "M3.4 PACKAGE 0 COMPLETE" -ForegroundColor Green
git status --short
