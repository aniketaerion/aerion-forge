from forge.autonomous_memory.feedback import (
    FeedbackOutcome,
    MemoryFeedback,
)
from forge.autonomous_memory.learning import (
    apply_feedback,
    create_learning_record,
)
from forge.autonomous_memory.models import (
    MemoryApplicability,
    MemoryRecord,
)
from forge.autonomous_memory.states import (
    ApplicabilityKind,
    MemoryKind,
    RetentionClass,
)


def applicability() -> MemoryApplicability:
    return MemoryApplicability(
        kind=ApplicabilityKind.EXACT_REPOSITORY,
        repository_scope="repository",
        rationale="Repository scoped.",
    )


def record() -> MemoryRecord:
    return MemoryRecord(
        memory_id="memory-1",
        memory_kind=MemoryKind.ENGINEERING_LESSON,
        statement="Use rollback checkpoints.",
        normalized_statement="use rollback checkpoints",
        confidence=0.8,
        repository_scope="repository",
        source_references=("source-1",),
        applicability=applicability(),
        retention_class=RetentionClass.LONG_LIVED,
    )


def test_feedback_updates_learning_counts() -> None:
    learning = create_learning_record(
        lesson="Use rollback checkpoints.",
        source_records=(record(),),
        applicability=applicability(),
        confidence=0.8,
    )
    feedback = MemoryFeedback(
        feedback_id="feedback-1",
        memory_id="memory-1",
        mission_id="mission-1",
        outcome=FeedbackOutcome.SUCCESS,
        validated=True,
        evidence_references=("evidence-1",),
        rationale="Rollback succeeded.",
    )

    result = apply_feedback(
        learning=learning,
        feedback=feedback,
    )

    assert result.learning.success_count == 1
    assert result.learning.failure_count == 0