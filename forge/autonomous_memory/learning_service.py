"""Application service for autonomous memory learning."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_memory.feedback import MemoryFeedback
from forge.autonomous_memory.learning import (
    LearningUpdate,
    apply_feedback,
    create_learning_record,
)
from forge.autonomous_memory.models import (
    LearningRecord,
    MemoryApplicability,
    MemoryRecord,
)
from forge.autonomous_memory.storage import MemoryStorage


@dataclass(slots=True)
class AutonomousLearningService:
    """Create and update learning records."""

    storage: MemoryStorage

    def create(
        self,
        *,
        lesson: str,
        source_records: tuple[MemoryRecord, ...],
        applicability: MemoryApplicability,
        confidence: float,
    ) -> LearningRecord:
        learning = create_learning_record(
            lesson=lesson,
            source_records=source_records,
            applicability=applicability,
            confidence=confidence,
        )
        self.storage.put_learning(learning)
        return learning

    def apply_feedback(
        self,
        *,
        learning: LearningRecord,
        feedback: MemoryFeedback,
    ) -> LearningUpdate:
        update = apply_feedback(
            learning=learning,
            feedback=feedback,
        )
        self.storage.put_learning(update.learning)
        return update