from forge.autonomous_memory.feedback import (
    FeedbackOutcome,
    MemoryFeedback,
)
from forge.autonomous_memory.learning_service import (
    AutonomousLearningService,
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
from forge.autonomous_memory.storage import (
    InMemoryMemoryStorage,
)


def test_learning_service_persists_learning() -> None:
    storage = InMemoryMemoryStorage()
    service = AutonomousLearningService(storage=storage)
    applicability = MemoryApplicability(
        kind=ApplicabilityKind.EXACT_REPOSITORY,
        repository_scope="repository",
        rationale="Repository scoped.",
    )
    record = MemoryRecord(
        memory_id="memory-1",
        memory_kind=MemoryKind.ENGINEERING_LESSON,
        statement="Use rollback checkpoints.",
        normalized_statement="use rollback checkpoints",
        confidence=0.8,
        repository_scope="repository",
        source_references=("source-1",),
        applicability=applicability,
        retention_class=RetentionClass.LONG_LIVED,
    )

    learning = service.create(
        lesson="Use rollback checkpoints.",
        source_records=(record,),
        applicability=applicability,
        confidence=0.8,
    )

    update = service.apply_feedback(
        learning=learning,
        feedback=MemoryFeedback(
            feedback_id="feedback-1",
            memory_id="memory-1",
            mission_id="mission-1",
            outcome=FeedbackOutcome.SUCCESS,
            validated=True,
            evidence_references=("evidence-1",),
            rationale="Rollback succeeded.",
        ),
    )

    assert update.learning.success_count == 1
    assert storage.all_learning()[0].success_count == 1