import pytest

from forge.autonomous_memory.errors import (
    MemorySupersessionError,
)
from forge.autonomous_memory.models import (
    MemoryApplicability,
    MemoryRecord,
)
from forge.autonomous_memory.states import (
    ApplicabilityKind,
    MemoryKind,
    MemoryStatus,
    RetentionClass,
)
from forge.autonomous_memory.supersession import (
    apply_supersession,
)


def record(
    memory_id: str,
    *,
    supersedes: str | None = None,
) -> MemoryRecord:
    return MemoryRecord(
        memory_id=memory_id,
        memory_kind=MemoryKind.HYPOTHESIS,
        statement="Possible constraint.",
        normalized_statement="possible constraint",
        confidence=0.5,
        repository_scope="repository",
        source_references=("source-1",),
        applicability=MemoryApplicability(
            kind=ApplicabilityKind.EXACT_REPOSITORY,
            repository_scope="repository",
            rationale="Repository scoped.",
        ),
        retention_class=RetentionClass.TEMPORARY,
        supersedes_memory_id=supersedes,
    )


def test_supersession_preserves_history() -> None:
    previous = record("memory-1")
    replacement = record(
        "memory-2",
        supersedes="memory-1",
    )

    result = apply_supersession(
        previous=previous,
        replacement=replacement,
        existing_records=(previous,),
    )

    assert (
        result.superseded.status
        is MemoryStatus.SUPERSEDED
    )
    assert result.replacement.memory_id == "memory-2"


def test_cross_repository_supersession_is_rejected() -> None:
    previous = record("memory-1")
    replacement = record(
        "memory-2",
        supersedes="memory-1",
    ).model_copy(
        update={"repository_scope": "other"}
    )

    with pytest.raises(MemorySupersessionError):
        apply_supersession(
            previous=previous,
            replacement=replacement,
            existing_records=(previous,),
        )