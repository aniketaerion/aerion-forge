import pytest

from forge.autonomous_memory.errors import MemoryScopeError
from forge.autonomous_memory.models import (
    MemoryApplicability,
    MemoryProvenance,
    MemoryRecord,
)
from forge.autonomous_memory.repository import MemoryRepository
from forge.autonomous_memory.states import (
    ApplicabilityKind,
    MemoryKind,
    MemorySourceKind,
    RetentionClass,
)
from forge.autonomous_memory.storage import (
    InMemoryMemoryStorage,
)


def test_repository_rejects_cross_scope_memory() -> None:
    storage = InMemoryMemoryStorage()
    repository = MemoryRepository(
        storage=storage,
        repository_scope="repository-a",
    )
    record = MemoryRecord(
        memory_id="memory-1",
        memory_kind=MemoryKind.HYPOTHESIS,
        statement="Possible constraint.",
        normalized_statement="possible constraint",
        confidence=0.5,
        repository_scope="repository-b",
        source_references=("source-1",),
        applicability=MemoryApplicability(
            kind=ApplicabilityKind.EXACT_REPOSITORY,
            repository_scope="repository-b",
            rationale="Repository scoped.",
        ),
        retention_class=RetentionClass.TEMPORARY,
    )
    provenance = MemoryProvenance(
        provenance_id="provenance-1",
        memory_id="memory-1",
        source_kind=MemorySourceKind.REPOSITORY,
        source_reference="source-1",
        evidence_digest="digest-1",
        repository_fingerprint="fingerprint-1",
        actor="Aerion",
    )

    with pytest.raises(MemoryScopeError):
        repository.save(record, provenance)