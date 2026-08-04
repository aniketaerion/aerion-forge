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