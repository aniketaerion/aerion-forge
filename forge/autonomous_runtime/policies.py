"""Bounded execution and authority policies."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from forge.autonomous_runtime.errors import MissionPolicyError
from forge.autonomous_runtime.states import (
    AuthorityLevel,
    RiskClass,
)


class RuntimeBudgetPolicy(BaseModel):
    """Finite mission execution budgets."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    maximum_steps: int = Field(default=20, ge=1, le=500)
    maximum_attempts_per_step: int = Field(default=2, ge=1, le=10)
    maximum_replans: int = Field(default=2, ge=0, le=10)
    maximum_rollback_attempts: int = Field(default=1, ge=0, le=5)
    maximum_tool_calls: int = Field(default=200, ge=1, le=5000)
    maximum_execution_cycles: int = Field(default=20, ge=1, le=500)
    time_budget_seconds: int = Field(default=3600, ge=30, le=604800)

    @model_validator(mode="after")
    def validate_relationships(self) -> RuntimeBudgetPolicy:
        if self.maximum_execution_cycles < self.maximum_steps:
            raise ValueError(
                "maximum_execution_cycles must be at least maximum_steps."
            )
        return self


class AuthorityPolicy(BaseModel):
    """Default authority ceiling and explicit-approval boundary."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    autonomous_ceiling: AuthorityLevel = AuthorityLevel.A2_MODIFY
    automatic_validation_authority: AuthorityLevel = (
        AuthorityLevel.A3_EXECUTE
    )
    explicit_approval_from: AuthorityLevel = AuthorityLevel.A4_COMMIT
    high_risk_from: RiskClass = RiskClass.R3_HIGH

    @model_validator(mode="after")
    def validate_authority_order(self) -> AuthorityPolicy:
        if (
            self.autonomous_ceiling
            >= self.explicit_approval_from
        ):
            raise ValueError(
                "Autonomous authority ceiling must remain below "
                "the explicit-approval boundary."
            )
        return self


class AutonomousRuntimePolicy(BaseModel):
    """Top-level immutable runtime policy."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = "1.0"
    budgets: RuntimeBudgetPolicy = Field(
        default_factory=RuntimeBudgetPolicy
    )
    authority: AuthorityPolicy = Field(
        default_factory=AuthorityPolicy
    )
    network_access_allowed: bool = False
    unrestricted_shell_allowed: bool = False
    unrestricted_mutation_allowed: bool = False
    require_verified_checkpoint_for_mutation: bool = True
    require_read_only_reviewer: bool = True
    single_writer_required: bool = True

    @model_validator(mode="after")
    def validate_safety_invariants(self) -> AutonomousRuntimePolicy:
        violations: list[str] = []

        if self.network_access_allowed:
            violations.append("network access must be denied by default")
        if self.unrestricted_shell_allowed:
            violations.append("unrestricted shell must remain disabled")
        if self.unrestricted_mutation_allowed:
            violations.append(
                "unrestricted autonomous mutation must remain disabled"
            )
        if not self.require_verified_checkpoint_for_mutation:
            violations.append(
                "verified checkpoints are required before mutation"
            )
        if not self.require_read_only_reviewer:
            violations.append("the reviewer must remain read-only")
        if not self.single_writer_required:
            violations.append("M5.1 requires a single writer")

        if violations:
            raise MissionPolicyError("; ".join(violations))

        return self