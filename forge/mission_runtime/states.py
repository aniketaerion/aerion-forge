"""State enumerations for the M5.8 Forge Mission Runtime."""

from __future__ import annotations

from enum import StrEnum


class MissionState(StrEnum):
    CREATED = "created"
    RESOLVING_WORKSPACE = "resolving_workspace"
    UNDERSTANDING_REPOSITORY = "understanding_repository"
    SELECTING_CAPABILITIES = "selecting_capabilities"
    RETRIEVING_CONTEXT = "retrieving_context"
    PLANNING = "planning"
    VALIDATING_PLAN = "validating_plan"
    AWAITING_PLAN_APPROVAL = "awaiting_plan_approval"
    APPROVED = "approved"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    RECOVERING = "recovering"
    DOCUMENTING = "documenting"
    GENERATING_REVIEW = "generating_review"
    AWAITING_FINAL_APPROVAL = "awaiting_final_approval"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MissionApprovalKind(StrEnum):
    PLAN = "plan"
    FINAL = "final"


class MissionApprovalDecision(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class MissionEvidenceKind(StrEnum):
    REPOSITORY = "repository"
    CAPABILITY = "capability"
    MEMORY = "memory"
    PLAN = "plan"
    APPROVAL = "approval"
    EXECUTION = "execution"
    VERIFICATION = "verification"
    DOCUMENTATION = "documentation"
    REVIEW = "review"
    RECOVERY = "recovery"


class MissionRisk(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MissionResultStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"