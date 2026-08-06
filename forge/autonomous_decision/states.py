"""Enumerations for the autonomous decision engine."""

from __future__ import annotations

from enum import StrEnum


class DecisionKind(StrEnum):
    """Decision categories supported by M5.4."""

    NEXT_ACTION = "next_action"
    RECOVERY = "recovery"
    COMPLETION = "completion"
    APPROVAL = "approval"
    STOP = "stop"


class DecisionDisposition(StrEnum):
    """Committed decision dispositions."""

    SELECT_ACTION = "select_action"
    RETRY = "retry"
    ROLLBACK = "rollback"
    REPLAN = "replan"
    PAUSE = "pause"
    ESCALATE = "escalate"
    COMPLETE = "complete"
    CANCEL = "cancel"
    NO_SAFE_ACTION = "no_safe_action"


class CandidateActionKind(StrEnum):
    """Candidate engineering action kinds."""

    EXECUTE_NEXT_STEP = "execute_next_step"
    RETRY_CURRENT_STEP = "retry_current_step"
    ROLLBACK_CURRENT_STEP = "rollback_current_step"
    REPLAN_REMAINING_WORK = "replan_remaining_work"
    REQUEST_APPROVAL = "request_approval"
    PAUSE_MISSION = "pause_mission"
    ESCALATE_MISSION = "escalate_mission"
    COMPLETE_MISSION = "complete_mission"
    CANCEL_MISSION = "cancel_mission"


class CandidateSource(StrEnum):
    """Provenance of a generated candidate."""

    APPROVED_PLAN = "approved_plan"
    ORCHESTRATION_STATE = "orchestration_state"
    EXECUTION_OUTCOME = "execution_outcome"
    VALIDATION_FINDING = "validation_finding"
    RECOVERY_POLICY = "recovery_policy"
    REPOSITORY_EVIDENCE = "repository_evidence"
    HUMAN_INSTRUCTION = "human_instruction"


class CandidateRejectionReason(StrEnum):
    """Canonical hard-rejection reasons."""

    DUPLICATE = "duplicate"
    INFEASIBLE = "infeasible"
    MISSING_DEPENDENCY = "missing_dependency"
    INSUFFICIENT_AUTHORITY = "insufficient_authority"
    APPROVAL_REQUIRED = "approval_required"
    SCOPE_VIOLATION = "scope_violation"
    RISK_THRESHOLD_EXCEEDED = "risk_threshold_exceeded"
    CONFIDENCE_BELOW_THRESHOLD = "confidence_below_threshold"
    EVIDENCE_INSUFFICIENT = "evidence_insufficient"
    COMPLETED_STEP_REPLAY = "completed_step_replay"
    BUDGET_EXHAUSTED = "budget_exhausted"
    POLICY_VIOLATION = "policy_violation"


class DecisionStopKind(StrEnum):
    """Explicit stop outcomes."""

    APPROVAL_REQUIRED = "approval_required"
    CLARIFICATION_REQUIRED = "clarification_required"
    EVIDENCE_REQUIRED = "evidence_required"
    POLICY_BLOCKED = "policy_blocked"
    RISK_TOO_HIGH = "risk_too_high"
    NO_SAFE_ACTION = "no_safe_action"
    MISSION_COMPLETE = "mission_complete"
    CANCELLED = "cancelled"