"""Learning-record creation and feedback updates."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_memory.feedback import (
    FeedbackOutcome,
    MemoryFeedback,
    assert_feedback_is_usable,
)
from forge.autonomous_memory.identifiers import (
    learning_record_identifier,
)
from forge.autonomous_memory.models import (
    LearningRecord,
    MemoryApplicability,
    MemoryRecord,
)


@dataclass(frozen=True, slots=True)
class LearningUpdate:
    """Updated learning record and attribution summary."""

    learning: LearningRecord
    feedback: MemoryFeedback


def create_learning_record(
    *,
    lesson: str,
    source_records: tuple[MemoryRecord, ...],
    applicability: MemoryApplicability,
    confidence: float,
) -> LearningRecord:
    """Create evidence-backed learning from source memories."""
    if not source_records:
        raise ValueError(
            "Learning requires at least one source memory."
        )

    source_ids = tuple(
        sorted(
            {
                record.memory_id
                for record in source_records
            }
        )
    )

    payload = {
        "lesson": lesson,
        "source_memory_ids": source_ids,
        "repository_scope": applicability.repository_scope,
    }

    return LearningRecord(
        learning_id=learning_record_identifier(payload),
        source_memory_ids=source_ids,
        lesson=lesson,
        success_count=0,
        failure_count=0,
        confidence=confidence,
        applicability=applicability,
    )


def apply_feedback(
    *,
    learning: LearningRecord,
    feedback: MemoryFeedback,
) -> LearningUpdate:
    """Update success/failure counts and confidence."""
    assert_feedback_is_usable(feedback)

    success_count = learning.success_count
    failure_count = learning.failure_count

    if feedback.outcome is FeedbackOutcome.SUCCESS:
        success_count += 1
    else:
        failure_count += 1

    total = success_count + failure_count
    empirical = (
        success_count / total
        if total
        else learning.confidence
    )

    confidence = round(
        max(
            0.0,
            min(
                1.0,
                0.5 * learning.confidence
                + 0.5 * empirical,
            ),
        ),
        6,
    )

    updated = learning.model_copy(
        update={
            "success_count": success_count,
            "failure_count": failure_count,
            "confidence": confidence,
        }
    )

    return LearningUpdate(
        learning=updated,
        feedback=feedback,
    )