"""Policies for the M5.8 Forge Mission Runtime."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class MissionLimits(BaseModel):
    model_config = ConfigDict(frozen=True)

    maximum_state_transitions: int = Field(
        default=100,
        ge=1,
        le=1000,
    )
    maximum_recovery_cycles: int = Field(
        default=3,
        ge=0,
        le=20,
    )
    maximum_selected_capabilities: int = Field(
        default=50,
        ge=1,
        le=500,
    )
    maximum_evidence_items: int = Field(
        default=2000,
        ge=1,
        le=20000,
    )


class MissionApprovalPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    require_plan_approval_for_high_risk: bool = True
    require_plan_approval_for_destructive_changes: bool = True
    require_final_approval_for_merge_worthy_work: bool = True
    require_final_approval_for_release: bool = True


class MissionSafetyPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    require_active_workspace: bool = True
    require_repository_scope_match: bool = True
    require_registered_capabilities: bool = True
    require_verification_before_completion: bool = True
    stop_on_blocking_failure: bool = True
    allow_unrestricted_git_operations: bool = False
    allow_self_modification: bool = False
    allow_scope_expansion_without_approval: bool = False


class MissionRuntimePolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    limits: MissionLimits = Field(
        default_factory=MissionLimits
    )
    approvals: MissionApprovalPolicy = Field(
        default_factory=MissionApprovalPolicy
    )
    safety: MissionSafetyPolicy = Field(
        default_factory=MissionSafetyPolicy
    )