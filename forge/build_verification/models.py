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