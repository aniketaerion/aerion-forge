from forge.autonomous_memory.deduplication import deduplicate_records
from forge.autonomous_memory.models import (
    MemoryApplicability,
    MemoryRecord,
)
from forge.autonomous_memory.states import (
    ApplicabilityKind,
    MemoryKind,
    RetentionClass,
)


def record(memory_id: str) -> MemoryRecord:
    applicability = MemoryApplicability(
        kind=ApplicabilityKind.EXACT_REPOSITORY,
        repository_scope="repository",
        rationale="Repository scoped.",
    )
    return MemoryRecord(
        memory_id=memory_id,
        memory_kind=MemoryKind.REPOSITORY_FACT,
        statement="Repository uses Python.",
        normalized_statement="repository uses python",
        confidence=0.9,
        repository_scope="repository",
        evidence_references=("evidence-1",),
        source_references=("source-1",),
        applicability=applicability,
        retention_class=RetentionClass.PROJECT_LIFETIME,
    )


def test_exact_duplicates_are_removed() -> None:
    result = deduplicate_records(
        (record("memory-2"), record("memory-1"))
    )
    assert len(result.records) == 1
    assert result.duplicate_memory_ids == ("memory-2",)