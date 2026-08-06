"""Immutable contracts for the Aerion Forge autonomous runtime."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from forge.autonomous_runtime.policies import RuntimeBudgetPolicy
from forge.autonomous_runtime.states import (
    AuthorityLevel,
    MissionDecision,
    MissionState,
    RecoveryAction,
    ReviewDecision,
    RiskClass,
    StepStatus,
    ValidationStatus,
)


def utc_now() -> datetime:
    return datetime.now(UTC)


class FrozenContract(BaseModel):
    """Base class for immutable autonomous-runtime contracts."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        use_enum_values=False,
    )


class MissionRequest(FrozenContract):
    request_id: str = Field(min_length=1)
    schema_version: str = "1.0"
    objective: str = Field(min_length=1)
    repository_root: str = Field(min_length=1)
    requested_scope: tuple[str, ...] = ()
    excluded_scope: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    acceptance_criteria: tuple[str, ...] = ()
    requested_authority: AuthorityLevel = AuthorityLevel.A1_PLAN
    budgets: RuntimeBudgetPolicy = Field(
        default_factory=RuntimeBudgetPolicy
    )
    requested_by: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_scope(self) -> MissionRequest:
        overlap = set(self.requested_scope).intersection(
            self.excluded_scope
        )
        if overlap:
            raise ValueError(
                "Requested and excluded scope overlap: "
                + ", ".join(sorted(overlap))
            )
        return self


class MissionContext(FrozenContract):
    context_id: str = Field(min_length=1)
    mission_id: str = Field(min_length=1)
    repository_fingerprint: str = Field(min_length=1)
    relevant_files: tuple[str, ...] = ()
    relevant_symbols: tuple[str, ...] = ()
    dependency_edges: tuple[tuple[str, str], ...] = ()
    architecture_constraints: tuple[str, ...] = ()
    business_rules: tuple[str, ...] = ()
    existing_tests: tuple[str, ...] = ()
    validation_commands: tuple[str, ...] = ()
    known_risks: tuple[str, ...] = ()
    knowledge_references: tuple[str, ...] = ()
    source_provenance: tuple[str, ...] = ()
    created_at: datetime = Field(default_factory=utc_now)


class MissionStep(FrozenContract):
    step_id: str = Field(min_length=1)
    plan_id: str = Field(min_length=1)
    sequence: int = Field(ge=1)
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    status: StepStatus = StepStatus.PENDING
    action_kind: str = Field(min_length=1)
    preconditions: tuple[str, ...] = ()
    expected_outputs: tuple[str, ...] = ()
    expected_files: tuple[str, ...] = ()
    prohibited_files: tuple[str, ...] = ()
    required_authority: AuthorityLevel = AuthorityLevel.A1_PLAN
    risk_class: RiskClass = RiskClass.R1_LOW
    approval_required: bool = False
    validation_requirements: tuple[str, ...] = ()
    checkpoint_required: bool = False
    attempt_budget: int = Field(default=2, ge=1, le=10)
    timeout_seconds: int = Field(default=300, ge=1, le=86400)
    depends_on: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_file_scope(self) -> MissionStep:
        overlap = set(self.expected_files).intersection(
            self.prohibited_files
        )
        if overlap:
            raise ValueError(
                "Expected and prohibited files overlap: "
                + ", ".join(sorted(overlap))
            )
        if (
            self.required_authority >= AuthorityLevel.A2_MODIFY
            and not self.checkpoint_required
        ):
            raise ValueError(
                "Modifying steps require a checkpoint."
            )
        return self


class MissionPlan(FrozenContract):
    plan_id: str = Field(min_length=1)
    mission_id: str = Field(min_length=1)
    version: int = Field(default=1, ge=1)
    objective_summary: str = Field(min_length=1)
    steps: tuple[MissionStep, ...] = ()
    expected_files: tuple[str, ...] = ()
    prohibited_files: tuple[str, ...] = ()
    required_validations: tuple[str, ...] = ()
    completion_criteria: tuple[str, ...] = Field(min_length=1)
    risk_class: RiskClass = RiskClass.R1_LOW
    required_authority: AuthorityLevel = AuthorityLevel.A1_PLAN
    created_at: datetime = Field(default_factory=utc_now)
    approved_at: datetime | None = None

    @model_validator(mode="after")
    def validate_plan(self) -> MissionPlan:
        sequences = [step.sequence for step in self.steps]
        if len(sequences) != len(set(sequences)):
            raise ValueError("Mission step sequences must be unique.")
        overlap = set(self.expected_files).intersection(
            self.prohibited_files
        )
        if overlap:
            raise ValueError(
                "Plan expected and prohibited files overlap."
            )
        highest_authority = max(
            (
                step.required_authority
                for step in self.steps
            ),
            default=AuthorityLevel.A0_READ,
        )
        if self.required_authority < highest_authority:
            raise ValueError(
                "Plan authority is below a step authority requirement."
            )
        return self


class ApprovalDecision(FrozenContract):
    approval_id: str = Field(min_length=1)
    mission_id: str = Field(min_length=1)
    plan_id: str | None = None
    step_id: str | None = None
    decision: str = Field(min_length=1)
    authority_granted: AuthorityLevel
    scope: tuple[str, ...] = ()
    conditions: tuple[str, ...] = ()
    approved_by: str = Field(min_length=1)
    issued_at: datetime = Field(default_factory=utc_now)
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    reason: str = ""

    @property
    def active(self) -> bool:
        now = utc_now()
        return (
            self.revoked_at is None
            and (
                self.expires_at is None
                or self.expires_at > now
            )
        )


class ToolInvocation(FrozenContract):
    invocation_id: str = Field(min_length=1)
    mission_id: str = Field(min_length=1)
    step_id: str = Field(min_length=1)
    tool_name: str = Field(min_length=1)
    action_kind: str = Field(min_length=1)
    arguments_digest: str = Field(min_length=1)
    redacted_arguments: dict[str, Any] = Field(default_factory=dict)
    required_authority: AuthorityLevel
    approval_id: str | None = None
    started_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None
    exit_code: int | None = None
    stdout_reference: str | None = None
    stderr_reference: str | None = None
    affected_files: tuple[str, ...] = ()
    result_digest: str | None = None
    status: str = "pending"


class ValidationEvidence(FrozenContract):
    evidence_id: str = Field(min_length=1)
    mission_id: str = Field(min_length=1)
    step_id: str | None = None
    check_name: str = Field(min_length=1)
    check_kind: str = Field(min_length=1)
    required: bool = True
    status: ValidationStatus
    command: str | None = None
    exit_code: int | None = None
    summary: str = ""
    metrics: dict[str, int | float | str | bool] = Field(
        default_factory=dict
    )
    artifact_references: tuple[str, ...] = ()
    repository_fingerprint: str = Field(min_length=1)
    started_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None


class MissionCheckpoint(FrozenContract):
    checkpoint_id: str = Field(min_length=1)
    mission_id: str = Field(min_length=1)
    step_id: str | None = None
    kind: str = Field(min_length=1)
    repository_fingerprint: str = Field(min_length=1)
    git_head: str | None = None
    working_tree_digest: str = Field(min_length=1)
    file_snapshot_references: tuple[str, ...] = ()
    created_at: datetime = Field(default_factory=utc_now)
    verified: bool = False
    restoration_test: str | None = None


class MissionEvent(FrozenContract):
    event_id: str = Field(min_length=1)
    schema_version: str = "1.0"
    mission_id: str = Field(min_length=1)
    sequence: int = Field(ge=1)
    event_type: str = Field(min_length=1)
    previous_state: MissionState | None = None
    new_state: MissionState
    actor: str = Field(min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str | None = None
    causation_id: str | None = None
    occurred_at: datetime = Field(default_factory=utc_now)


class RecoveryDecision(FrozenContract):
    recovery_id: str = Field(min_length=1)
    mission_id: str = Field(min_length=1)
    step_id: str | None = None
    failure_class: str = Field(min_length=1)
    action: RecoveryAction
    checkpoint_id: str | None = None
    attempt_number: int = Field(ge=1)
    reason: str = Field(min_length=1)
    approved_by: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class MissionOutcome(FrozenContract):
    outcome_id: str = Field(min_length=1)
    mission_id: str = Field(min_length=1)
    terminal_state: MissionState
    objective_satisfied: bool
    completed_step_ids: tuple[str, ...] = ()
    changed_files: tuple[str, ...] = ()
    validation_evidence_ids: tuple[str, ...] = ()
    unresolved_findings: tuple[str, ...] = ()
    review_decision: ReviewDecision
    report_references: tuple[str, ...] = ()
    completed_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_terminal_outcome(self) -> MissionOutcome:
        if self.terminal_state not in {
            MissionState.COMPLETED,
            MissionState.FAILED,
            MissionState.CANCELLED,
        }:
            raise ValueError(
                "Mission outcome requires a terminal state."
            )
        if (
            self.terminal_state is MissionState.COMPLETED
            and (
                not self.objective_satisfied
                or self.review_decision is not ReviewDecision.APPROVE
                or self.unresolved_findings
            )
        ):
            raise ValueError(
                "Completed outcomes require objective satisfaction, "
                "approved review, and no unresolved findings."
            )
        return self


class AutonomousMission(FrozenContract):
    mission_id: str = Field(min_length=1)
    schema_version: str = "1.0"
    version: int = Field(default=1, ge=1)
    request: MissionRequest
    state: MissionState = MissionState.RECEIVED
    qualification_decision: MissionDecision | None = None
    risk_class: RiskClass = RiskClass.R0_READ_ONLY
    granted_authority: AuthorityLevel = AuthorityLevel.A0_READ
    approval_state: str = "not_required"
    context_id: str | None = None
    plan_id: str | None = None
    current_step_id: str | None = None
    attempt_count: int = Field(default=0, ge=0)
    replan_count: int = Field(default=0, ge=0)
    tool_call_count: int = Field(default=0, ge=0)
    checkpoint_ids: tuple[str, ...] = ()
    event_sequence: int = Field(default=0, ge=0)
    validation_evidence_ids: tuple[str, ...] = ()
    finding_ids: tuple[str, ...] = ()
    outcome_id: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_authority(self) -> AutonomousMission:
        if self.granted_authority > self.request.requested_authority:
            raise ValueError(
                "Granted authority exceeds requested authority."
            )
        if (
            self.state in {
                MissionState.COMPLETED,
                MissionState.FAILED,
                MissionState.CANCELLED,
            }
            and self.outcome_id is None
        ):
            raise ValueError(
                "Terminal missions require an outcome identifier."
            )
        return self