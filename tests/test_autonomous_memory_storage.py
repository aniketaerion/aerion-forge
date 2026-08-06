import pytest

from forge.autonomous_memory.errors import MemoryContractError
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


def record(statement: str) -> MemoryRecord:
    return MemoryRecord(
        memory_id="memory-1",
        memory_kind=MemoryKind.HYPOTHESIS,
        statement=statement,
        normalized_statement=statement.casefold(),
        confidence=0.5,
        repository_scope="repository",
        source_references=("source-1",),
        applicability=MemoryApplicability(
            kind=ApplicabilityKind.EXACT_REPOSITORY,
            repository_scope="repository",
            rationale="Repository scoped.",
        ),
        retention_class=RetentionClass.TEMPORARY,
    )


def test_identical_write_is_idempotent() -> None:
    storage = InMemoryMemoryStorage()
    item = record("Possible constraint.")

    storage.put_record(item)
    storage.put_record(item)

    assert storage.get_record("memory-1") == item


def test_conflicting_write_is_rejected() -> None:
    storage = InMemoryMemoryStorage()
    storage.put_record(record("First statement."))

    with pytest.raises(MemoryContractError):
        storage.put_record(record("Different statement."))