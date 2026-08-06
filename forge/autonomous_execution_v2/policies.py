"""Default-safe policies for M5.7 execution."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ExecutionLimits(BaseModel):
    model_config = ConfigDict(frozen=True)

    maximum_steps: int = Field(default=100, ge=1, le=1000)
    maximum_attempts_per_step: int = Field(
        default=3,
        ge=1,
        le=20,
    )
    maximum_evidence_items: int = Field(
        default=1000,
        ge=1,
        le=10000,
    )


class ExecutionSafetyPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    require_approved_plan: bool = True
    require_repository_scope_match: bool = True
    require_evidence_for_success: bool = True
    allow_destructive_execution: bool = False
    require_approval_for_high_risk: bool = True
    stop_on_blocking_failure: bool = True


class AutonomousExecutionV2Policy(BaseModel):
    model_config = ConfigDict(frozen=True)

    limits: ExecutionLimits = Field(
        default_factory=ExecutionLimits
    )
    safety: ExecutionSafetyPolicy = Field(
        default_factory=ExecutionSafetyPolicy
    )