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