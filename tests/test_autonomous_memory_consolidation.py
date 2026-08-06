from forge.autonomous_memory.consolidation import (
    consolidate_records,
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


def record(
    memory_id: str,
    confidence: float,
) -> MemoryRecord:
    return MemoryRecord(
        memory_id=memory_id,
        memory_kind=MemoryKind.HYPOTHESIS,
        statement="Possible constraint.",
        normalized_statement="possible constraint",
        confidence=confidence,
        repository_scope="repository",
        source_references=("source-1",),
        applicability=MemoryApplicability(
            kind=ApplicabilityKind.EXACT_REPOSITORY,
            repository_scope="repository",
            rationale="Repository scoped.",
        ),
        retention_class=RetentionClass.TEMPORARY,
    )


def test_highest_confidence_record_is_canonical() -> None:
    groups = consolidate_records(
        (
            record("memory-1", 0.5),
            record("memory-2", 0.8),
        )
    )

    assert len(groups) == 1
    assert groups[0].canonical.memory_id == "memory-2"
    assert len(groups[0].members) == 2