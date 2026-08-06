"""Immutable M5.7 autonomous execution contracts."""

from __future__ import annotations

from datetime import UTC, datetime

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
    return datetime.now(UTC)


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
    def validate_request(self) -> ExecutionRequest:
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
    def validate_dependency(self) -> ExecutionDependency:
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
    def validate_step(self) -> ExecutionStep:
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
    def validate_evidence(self) -> ExecutionEvidence:
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
    def validate_run(self) -> ExecutionRun:
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