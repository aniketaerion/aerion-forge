"""Immutable contracts for autonomous execution."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from forge.autonomous_execution.states import (
    TERMINAL_EXECUTION_STATES,
    ExecutionFailureClass,
    StepExecutionState,
)
from forge.autonomous_execution.tool_contracts import (
    ToolExecutionResult,
)


def utc_now() -> datetime:
    return datetime.now(UTC)


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