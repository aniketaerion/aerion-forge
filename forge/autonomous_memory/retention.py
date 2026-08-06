"""Retention and status filtering."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from forge.autonomous_memory.models import MemoryRecord
from forge.autonomous_memory.states import (
    MemoryStatus,
    RetentionClass,
)


@dataclass(frozen=True, slots=True)
class RetentionDecision:
    """Retention decision for one memory record."""

    retain: bool
    target_status: MemoryStatus
    rationale: str


def evaluate_retention(
    record: MemoryRecord,
    *,
    maximum_temporary_age_days: int = 30,
) -> RetentionDecision:
    """Evaluate deterministic retention policy."""
    if record.status in {
        MemoryStatus.QUARANTINED,
        MemoryStatus.DISPUTED,
    }:
        return RetentionDecision(
            retain=True,
            target_status=record.status,
            rationale="Exceptional status remains retained.",
        )

    if record.retention_class is not RetentionClass.TEMPORARY:
        return RetentionDecision(
            retain=True,
            target_status=record.status,
            rationale="Non-temporary memory remains retained.",
        )

    age_days = (
        datetime.now(UTC) - record.created_at
    ).total_seconds() / 86400.0

    if age_days > maximum_temporary_age_days:
        return RetentionDecision(
            retain=True,
            target_status=MemoryStatus.EXPIRED,
            rationale="Temporary memory exceeded retention age.",
        )

    return RetentionDecision(
        retain=True,
        target_status=record.status,
        rationale="Temporary memory remains within retention age.",
    )