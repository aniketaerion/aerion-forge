"""Immutable contracts for the autonomous decision engine."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from forge.autonomous_decision.states import (
    CandidateActionKind,
    CandidateRejectionReason,
    CandidateSource,
    DecisionDisposition,
    DecisionKind,
    DecisionStopKind,
)


def utc_now() -> datetime:
    return datetime.now(UTC)


class FrozenDecisionContract(BaseModel):
    """Base immutable decision contract."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class DecisionRequest(FrozenDecisionContract):
    """Request for one bounded autonomous engineering decision."""

    request_id: str = Field(min_length=1)
    schema_version: str = "1.0"
    mission_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    plan_id: str = Field(min_length=1)
    plan_version: int = Field(ge=1)
    repository_root: str = Field(min_length=1)
    decision_kind: DecisionKind = DecisionKind.NEXT_ACTION
    maximum_candidates: int = Field(default=20, ge=1, le=200)
    dry_run: bool = True
    requested_by: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=utc_now)


class DecisionContext(FrozenDecisionContract):
    """Evidence-bearing decision context."""

    context_id: str = Field(min_length=1)
    schema_version: str = "1.0"
    mission_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    mission_state: str = Field(min_length=1)
    orchestration_state: str = Field(min_length=1)
    current_step_id: str | None = None
    completed_step_ids: tuple[str, ...] = ()
    failed_step_ids: tuple[str, ...] = ()
    retry_count: int = Field(default=0, ge=0)
    rollback_count: int = Field(default=0, ge=0)
    replan_count: int = Field(default=0, ge=0)
    authority_level: str = Field(min_length=1)
    approval_state: str = Field(min_length=1)
    repository_fingerprint: str = Field(min_length=1)
    evidence_references: tuple[str, ...] = ()
    unresolved_findings: tuple[str, ...] = ()
    policy_version: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_context_collections(
        self,
    ) -> DecisionContext:
        if len(set(self.completed_step_ids)) != len(
            self.completed_step_ids
        ):
            raise ValueError(
                "completed_step_ids cannot contain duplicates."
            )

        if len(set(self.failed_step_ids)) != len(
            self.failed_step_ids
        ):
            raise ValueError(
                "failed_step_ids cannot contain duplicates."
            )

        if set(self.completed_step_ids).intersection(
            self.failed_step_ids
        ):
            raise ValueError(
                "A step cannot be both completed and failed."
            )

        return self


class CandidateAction(FrozenDecisionContract):
    """One candidate engineering action."""

    candidate_id: str = Field(min_length=1)
    schema_version: str = "1.0"
    action_kind: CandidateActionKind
    target_step_id: str | None = None
    description: str = Field(min_length=1)
    required_authority: str = Field(min_length=1)
    approval_required: bool = False
    risk_class: str = Field(min_length=1)
    expected_effects: tuple[str, ...] = ()
    expected_cost: float = Field(default=0.0, ge=0.0)
    reversible: bool = True
    dependencies: tuple[str, ...] = ()
    evidence_references: tuple[str, ...] = ()
    source: CandidateSource
    created_at: datetime = Field(default_factory=utc_now)


class CandidateAssessment(FrozenDecisionContract):
    """Explainable assessment of one candidate."""

    assessment_id: str = Field(min_length=1)
    candidate_id: str = Field(min_length=1)
    feasible: bool
    policy_allowed: bool
    risk_score: float = Field(ge=0.0, le=1.0)
    confidence_score: float = Field(ge=0.0, le=1.0)
    evidence_score: float = Field(ge=0.0, le=1.0)
    utility_score: float = Field(ge=0.0, le=1.0)
    reversibility_score: float = Field(ge=0.0, le=1.0)
    total_score: float
    rejection_reasons: tuple[CandidateRejectionReason, ...] = ()
    warnings: tuple[str, ...] = ()
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_assessment_disposition(
        self,
    ) -> CandidateAssessment:
        accepted = self.feasible and self.policy_allowed

        if accepted and self.rejection_reasons:
            raise ValueError(
                "Accepted candidate cannot have rejection reasons."
            )

        if not accepted and not self.rejection_reasons:
            raise ValueError(
                "Rejected candidate requires at least one reason."
            )

        return self


class DecisionRecord(FrozenDecisionContract):
    """Immutable committed autonomous decision."""

    decision_id: str = Field(min_length=1)
    schema_version: str = "1.0"
    request_id: str = Field(min_length=1)
    context_id: str = Field(min_length=1)
    selected_candidate_id: str | None = None
    decision_kind: DecisionKind
    disposition: DecisionDisposition
    rationale: str = Field(min_length=1)
    alternative_candidate_ids: tuple[str, ...] = ()
    rejected_candidate_ids: tuple[str, ...] = ()
    assessment_ids: tuple[str, ...] = ()
    evidence_references: tuple[str, ...] = ()
    approval_required: bool = False
    confidence: float = Field(ge=0.0, le=1.0)
    context_fingerprint: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_selected_candidate(
        self,
    ) -> DecisionRecord:
        action_selected = (
            self.disposition is DecisionDisposition.SELECT_ACTION
        )

        if action_selected and self.selected_candidate_id is None:
            raise ValueError(
                "select_action decision requires selected_candidate_id."
            )

        if (
            self.disposition
            is DecisionDisposition.NO_SAFE_ACTION
            and self.selected_candidate_id is not None
        ):
            raise ValueError(
                "no_safe_action cannot select a candidate."
            )

        if (
            self.selected_candidate_id is not None
            and self.selected_candidate_id
            in self.rejected_candidate_ids
        ):
            raise ValueError(
                "Rejected candidate cannot be selected."
            )

        return self


class DecisionStop(FrozenDecisionContract):
    """Explicit stop produced when no action is selected."""

    stop_id: str = Field(min_length=1)
    request_id: str = Field(min_length=1)
    stop_kind: DecisionStopKind
    reason: str = Field(min_length=1)
    resumable: bool = False
    approval_required: bool = False
    evidence_references: tuple[str, ...] = ()
    created_at: datetime = Field(default_factory=utc_now)