"""Enumerations for M5.7 autonomous execution."""

from __future__ import annotations

from enum import StrEnum


class ExecutionRunState(StrEnum):
    CREATED = "created"
    VALIDATING = "validating"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    RECOVERING = "recovering"
    AWAITING_APPROVAL = "awaiting_approval"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExecutionStepState(StrEnum):
    PENDING = "pending"
    ELIGIBLE = "eligible"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class ExecutionAttemptState(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RecoveryAction(StrEnum):
    RETRY = "retry"
    PAUSE = "pause"
    SKIP = "skip"
    ROLLBACK = "rollback"
    REPLAN = "replan"
    ABORT = "abort"


class EvidenceKind(StrEnum):
    TOOL_RESULT = "tool_result"
    TEST_RESULT = "test_result"
    VALIDATION_RESULT = "validation_result"
    FILE_CHANGE = "file_change"
    CHECKPOINT = "checkpoint"
    REPORT = "report"