from forge.autonomous_memory.models import (
    MemoryApplicability,
    MemoryRecord,
)
from forge.autonomous_memory.retention import (
    evaluate_retention,
)
from forge.autonomous_memory.states import (
    ApplicabilityKind,
    MemoryKind,
    MemoryStatus,
    RetentionClass,
)


def test_permanent_memory_is_retained() -> None:
    record = MemoryRecord(
        memory_id="memory-1",
        memory_kind=MemoryKind.ARCHITECTURE_CONSTRAINT,
        statement="Execution requires approval.",
        normalized_statement="execution requires approval",
        confidence=0.9,
        repository_scope="repository",
        evidence_references=("evidence-1",),
        source_references=("source-1",),
        applicability=MemoryApplicability(
            kind=ApplicabilityKind.EXACT_REPOSITORY,
            repository_scope="repository",
            rationale="Repository scoped.",
        ),
        retention_class=RetentionClass.PERMANENT,
    )

    result = evaluate_retention(record)

    assert result.retain
    assert result.target_status is MemoryStatus.ACTIVE