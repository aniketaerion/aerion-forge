"""State and outcome enumerations for mission orchestration."""

from __future__ import annotations

from enum import StrEnum


class OrchestrationState(StrEnum):
    """Authoritative orchestration-session states."""

    CREATED = "created"
    INITIALIZING = "initializing"
    PLAN_LOADING = "plan_loading"
    READY = "ready"
    STEP_SELECTING = "step_selecting"
    STEP_PREPARING = "step_preparing"
    STEP_EXECUTING = "step_executing"
    OUTCOME_PROCESSING = "outcome_processing"
    PROGRESS_UPDATING = "progress_updating"
    CONTINUE_CHECK = "continue_check"
    AWAITING_APPROVAL = "awaiting_approval"
    RETRY_PENDING = "retry_pending"
    ROLLBACK_PENDING = "rollback_pending"
    REPLAN_PENDING = "replan_pending"
    PAUSED = "paused"
    RESUME_VALIDATING = "resume_validating"
    ESCALATED = "escalated"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class OrchestrationStopKind(StrEnum):
    """Explicit orchestration stop categories."""

    AWAITING_APPROVAL = "awaiting_approval"
    BLOCKED = "blocked"
    PAUSED = "paused"
    ESCALATED = "escalated"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class IterationOutcome(StrEnum):
    """Outcome of one bounded orchestration iteration."""

    STEP_SELECTED = "step_selected"
    STEP_SUCCEEDED = "step_succeeded"
    STEP_FAILED = "step_failed"
    DRY_RUN_COMPLETED = "dry_run_completed"
    RETRY_REQUIRED = "retry_required"
    ROLLBACK_REQUIRED = "rollback_required"
    REPLAN_REQUIRED = "replan_required"
    APPROVAL_REQUIRED = "approval_required"
    PAUSED = "paused"
    ESCALATED = "escalated"
    MISSION_COMPLETED = "mission_completed"
    NO_ELIGIBLE_STEP = "no_eligible_step"


TERMINAL_ORCHESTRATION_STATES: frozenset[OrchestrationState] = frozenset(
    {
        OrchestrationState.COMPLETED,
        OrchestrationState.FAILED,
        OrchestrationState.CANCELLED,
    }
)


RESUMABLE_ORCHESTRATION_STATES: frozenset[OrchestrationState] = frozenset(
    {
        OrchestrationState.PAUSED,
        OrchestrationState.AWAITING_APPROVAL,
        OrchestrationState.RETRY_PENDING,
        OrchestrationState.ROLLBACK_PENDING,
        OrchestrationState.REPLAN_PENDING,
        OrchestrationState.ESCALATED,
    }
)