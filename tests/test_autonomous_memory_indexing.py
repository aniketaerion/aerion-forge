from forge.autonomous_memory.indexing import MemoryIndex
from forge.autonomous_memory.models import (
    MemoryApplicability,
    MemoryRecord,
)
from forge.autonomous_memory.states import (
    ApplicabilityKind,
    MemoryKind,
    RetentionClass,
)


def test_index_filters_by_repository_and_tag() -> None:
    record = MemoryRecord(
        memory_id="memory-1",
        memory_kind=MemoryKind.HYPOTHESIS,
        statement="Possible constraint.",
        normalized_statement="possible constraint",
        confidence=0.5,
        repository_scope="repository",
        source_references=("source-1",),
        tags=("architecture",),
        applicability=MemoryApplicability(
            kind=ApplicabilityKind.EXACT_REPOSITORY,
            repository_scope="repository",
            rationale="Repository scoped.",
        ),
        retention_class=RetentionClass.TEMPORARY,
    )
    index = MemoryIndex()
    index.add(record)

    assert index.candidates(
        repository_scope="repository",
        tags=("architecture",),
    ) == ("memory-1",)