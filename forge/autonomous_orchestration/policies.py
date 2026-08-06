"""Bounded orchestration policies."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from forge.autonomous_orchestration.errors import (
    OrchestrationPolicyError,
)


class OrchestrationBudgetPolicy(BaseModel):
    """Finite mission-orchestration budgets."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    maximum_cycles: int = Field(default=25, ge=1, le=500)
    maximum_step_executions: int = Field(default=20, ge=1, le=500)
    maximum_retries: int = Field(default=3, ge=0, le=50)
    maximum_rollbacks: int = Field(default=2, ge=0, le=20)
    maximum_replans: int = Field(default=2, ge=0, le=20)
    maximum_resume_attempts: int = Field(default=3, ge=0, le=20)

    @model_validator(mode="after")
    def validate_budget_relationships(
        self,
    ) -> OrchestrationBudgetPolicy:
        if self.maximum_cycles < self.maximum_step_executions:
            raise ValueError(
                "maximum_cycles must cover maximum_step_executions."
            )

        recovery_budget = (
            self.maximum_retries
            + self.maximum_rollbacks
            + self.maximum_replans
        )
        if recovery_budget > self.maximum_cycles:
            raise ValueError(
                "Combined recovery budgets cannot exceed "
                "maximum_cycles."
            )

        return self


class OrchestrationSafetyPolicy(BaseModel):
    """Default-safe orchestration behaviour."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    dry_run_by_default: bool = True
    one_active_session_per_mission: bool = True
    one_execution_per_iteration: bool = True
    require_approved_plan: bool = True
    require_plan_version_match: bool = True
    require_verified_resume_checkpoint: bool = True
    require_optimistic_versioning: bool = True
    stop_on_approval_boundary: bool = True
    stop_on_scope_violation: bool = True
    stop_on_invariant_violation: bool = True
    allow_terminal_resume: bool = False
    allow_completed_step_replay: bool = False

    @model_validator(mode="after")
    def validate_safety_invariants(
        self,
    ) -> OrchestrationSafetyPolicy:
        violations: list[str] = []

        if not self.one_active_session_per_mission:
            violations.append(
                "one active session per mission is mandatory"
            )
        if not self.one_execution_per_iteration:
            violations.append(
                "one execution per iteration is mandatory"
            )
        if not self.require_approved_plan:
            violations.append("approved plan is mandatory")
        if not self.require_plan_version_match:
            violations.append("plan-version matching is mandatory")
        if not self.require_verified_resume_checkpoint:
            violations.append(
                "verified resume checkpoint is mandatory"
            )
        if not self.require_optimistic_versioning:
            violations.append(
                "optimistic versioning is mandatory"
            )
        if not self.stop_on_approval_boundary:
            violations.append(
                "approval boundaries must stop orchestration"
            )
        if not self.stop_on_scope_violation:
            violations.append(
                "scope violations must stop orchestration"
            )
        if not self.stop_on_invariant_violation:
            violations.append(
                "invariant violations must stop orchestration"
            )
        if self.allow_terminal_resume:
            violations.append(
                "terminal sessions cannot resume"
            )
        if self.allow_completed_step_replay:
            violations.append(
                "completed steps cannot be replayed"
            )

        if violations:
            raise OrchestrationPolicyError("; ".join(violations))

        return self


class AutonomousOrchestrationPolicy(BaseModel):
    """Top-level policy for M5.3 mission orchestration."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = "1.0"
    budgets: OrchestrationBudgetPolicy = Field(
        default_factory=OrchestrationBudgetPolicy
    )
    safety: OrchestrationSafetyPolicy = Field(
        default_factory=OrchestrationSafetyPolicy
    )