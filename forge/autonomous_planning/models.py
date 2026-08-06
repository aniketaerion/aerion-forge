"""Immutable contracts for autonomous planning."""

from __future__ import annotations

from datetime import UTC, datetime

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
    return datetime.now(UTC)


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
    def validate_request(self) -> PlanningRequest:
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
    def validate_dependency(self) -> PlanningDependency:
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
    def validate_step(self) -> PlanningStep:
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
    def validate_plan(self) -> PlanningPlan:
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
    def validate_result(self) -> PlanningValidationResult:
        if self.valid and any(finding.blocking for finding in self.findings):
            raise PlanningContractError(
                "Valid plan cannot contain blocking findings."
            )
        return self