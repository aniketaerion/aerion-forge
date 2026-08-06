"""Default-safe policies for autonomous engineering decisions."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from forge.autonomous_decision.errors import DecisionPolicyError


class DecisionThresholdPolicy(BaseModel):
    """Normalized score thresholds."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    maximum_candidates: int = Field(default=20, ge=1, le=200)
    maximum_risk_score: float = Field(default=0.60, ge=0.0, le=1.0)
    minimum_confidence_score: float = Field(
        default=0.55,
        ge=0.0,
        le=1.0,
    )
    minimum_evidence_score: float = Field(
        default=0.50,
        ge=0.0,
        le=1.0,
    )
    minimum_utility_score: float = Field(
        default=0.25,
        ge=0.0,
        le=1.0,
    )
    minimum_reversibility_for_mutation: float = Field(
        default=0.50,
        ge=0.0,
        le=1.0,
    )


class DecisionWeightPolicy(BaseModel):
    """Explicit deterministic scoring weights."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    utility_weight: float = Field(default=0.35, ge=0.0, le=1.0)
    confidence_weight: float = Field(default=0.25, ge=0.0, le=1.0)
    evidence_weight: float = Field(default=0.20, ge=0.0, le=1.0)
    reversibility_weight: float = Field(default=0.10, ge=0.0, le=1.0)
    risk_weight: float = Field(default=0.10, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_total_weight(
        self,
    ) -> DecisionWeightPolicy:
        total = (
            self.utility_weight
            + self.confidence_weight
            + self.evidence_weight
            + self.reversibility_weight
            + self.risk_weight
        )

        if abs(total - 1.0) > 1e-9:
            raise DecisionPolicyError(
                "Decision scoring weights must total exactly 1.0."
            )

        return self


class DecisionSafetyPolicy(BaseModel):
    """Hard safety requirements for decision selection."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    dry_run_by_default: bool = True
    require_evidence: bool = True
    require_scope_match: bool = True
    require_authority_match: bool = True
    preserve_approval_requirements: bool = True
    reject_completed_step_replay: bool = True
    reject_duplicate_candidates: bool = True
    reject_conflicting_replay: bool = True
    allow_tool_execution: bool = False
    allow_repository_mutation: bool = False
    allow_hidden_assumptions: bool = False

    @model_validator(mode="after")
    def validate_safety(
        self,
    ) -> DecisionSafetyPolicy:
        violations: list[str] = []

        if not self.require_evidence:
            violations.append("evidence is mandatory")
        if not self.require_scope_match:
            violations.append("scope matching is mandatory")
        if not self.require_authority_match:
            violations.append("authority matching is mandatory")
        if not self.preserve_approval_requirements:
            violations.append(
                "approval requirements must be preserved"
            )
        if not self.reject_completed_step_replay:
            violations.append(
                "completed-step replay must be rejected"
            )
        if not self.reject_duplicate_candidates:
            violations.append(
                "duplicate candidates must be rejected"
            )
        if not self.reject_conflicting_replay:
            violations.append(
                "conflicting decision replay must be rejected"
            )
        if self.allow_tool_execution:
            violations.append(
                "M5.4 cannot execute tools"
            )
        if self.allow_repository_mutation:
            violations.append(
                "M5.4 cannot mutate repository content"
            )
        if self.allow_hidden_assumptions:
            violations.append(
                "hidden assumptions are prohibited"
            )

        if violations:
            raise DecisionPolicyError("; ".join(violations))

        return self


class AutonomousDecisionPolicy(BaseModel):
    """Top-level M5.4 decision policy."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = "1.0"
    policy_version: str = "1.0"
    thresholds: DecisionThresholdPolicy = Field(
        default_factory=DecisionThresholdPolicy
    )
    weights: DecisionWeightPolicy = Field(
        default_factory=DecisionWeightPolicy
    )
    safety: DecisionSafetyPolicy = Field(
        default_factory=DecisionSafetyPolicy
    )