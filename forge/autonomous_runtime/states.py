"""Autonomous runtime enumerations."""

from __future__ import annotations

from enum import IntEnum, StrEnum


class MissionState(StrEnum):
    """Authoritative autonomous mission states."""

    RECEIVED = "received"
    QUALIFYING = "qualifying"
    CLARIFICATION_REQUIRED = "clarification_required"
    QUALIFIED = "qualified"
    CONTEXT_BUILDING = "context_building"
    CONTEXT_READY = "context_ready"
    PLANNING = "planning"
    PLAN_READY = "plan_ready"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    EXECUTING = "executing"
    VALIDATING = "validating"
    REVIEWING = "reviewing"
    PAUSED = "paused"
    BLOCKED = "blocked"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"
    ESCALATED = "escalated"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MissionDecision(StrEnum):
    """Qualification decisions."""

    ACCEPT = "accept"
    REQUEST_CLARIFICATION = "request_clarification"
    REJECT = "reject"
    ESCALATE = "escalate"


class RiskClass(IntEnum):
    """Ordered mission and action risk classes."""

    R0_READ_ONLY = 0
    R1_LOW = 1
    R2_MODERATE = 2
    R3_HIGH = 3
    R4_CRITICAL = 4
    R5_HUMAN_CONTROLLED = 5


class AuthorityLevel(IntEnum):
    """Ordered autonomous authority levels."""

    A0_READ = 0
    A1_PLAN = 1
    A2_MODIFY = 2
    A3_EXECUTE = 3
    A4_COMMIT = 4
    A5_PUSH = 5
    A6_MERGE_RELEASE = 6


class StepStatus(StrEnum):
    """Mission-step lifecycle status."""

    PENDING = "pending"
    READY = "ready"
    AWAITING_APPROVAL = "awaiting_approval"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"
    ROLLED_BACK = "rolled_back"
    CANCELLED = "cancelled"


class ValidationStatus(StrEnum):
    """Validation evidence status."""

    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"
    SKIP = "skip"
    UNAVAILABLE = "unavailable"
    ERROR = "error"


class ReviewDecision(StrEnum):
    """Independent mission-review decisions."""

    APPROVE = "approve"
    REVISE = "revise"
    ESCALATE = "escalate"
    REJECT = "reject"


class RecoveryAction(StrEnum):
    """Recovery actions available to the runtime."""

    RETRY_STEP = "retry_step"
    REPLAN = "replan"
    ROLLBACK_STEP = "rollback_step"
    ROLLBACK_MISSION = "rollback_mission"
    PAUSE = "pause"
    ESCALATE = "escalate"
    ABORT = "abort"


TERMINAL_MISSION_STATES: frozenset[MissionState] = frozenset(
    {
        MissionState.COMPLETED,
        MissionState.FAILED,
        MissionState.CANCELLED,
    }
)