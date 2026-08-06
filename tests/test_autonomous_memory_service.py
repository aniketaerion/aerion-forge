from forge.autonomous_memory.indexing import MemoryIndex
from forge.autonomous_memory.memory_service import (
    AutonomousMemoryService,
)
from forge.autonomous_memory.models import (
    MemoryObservation,
    MemoryQuery,
)
from forge.autonomous_memory.policies import (
    AutonomousMemoryPolicy,
)
from forge.autonomous_memory.states import MemorySourceKind
from forge.autonomous_memory.storage import (
    InMemoryMemoryStorage,
)


def test_service_ingests_and_retrieves_memory() -> None:
    service = AutonomousMemoryService(
        policy=AutonomousMemoryPolicy(),
        storage=InMemoryMemoryStorage(),
        index=MemoryIndex(),
    )

    result = service.ingest(
        MemoryObservation(
            observation_id="observation-1",
            source_kind=MemorySourceKind.REPOSITORY,
            source_reference="forge/module.py",
            repository_root="repository",
            repository_fingerprint="fingerprint-1",
            content="Repository uses Python.",
            evidence_references=("evidence-1",),
        ),
        actor="Aerion",
    )

    retrieved = service.retrieve(
        query=MemoryQuery(
            query_id="query-1",
            repository_scope="repository",
            requested_by="Aerion",
        ),
        query_text="python repository",
    )

    assert retrieved.records[0].memory_id == (
        result.record.memory_id
    )