from forge.autonomous_memory.models import (
    MemoryApplicability,
    MemoryQuery,
    MemoryRecord,
)
from forge.autonomous_memory.policies import (
    AutonomousMemoryPolicy,
)
from forge.autonomous_memory.retrieval import retrieve_memory
from forge.autonomous_memory.states import (
    ApplicabilityKind,
    MemoryKind,
    RetentionClass,
)
from forge.autonomous_memory.storage import (
    InMemoryMemoryStorage,
)


def test_retrieval_is_repository_scoped() -> None:
    storage = InMemoryMemoryStorage()

    for memory_id, repository in (
        ("memory-1", "repository-a"),
        ("memory-2", "repository-b"),
    ):
        storage.put_record(
            MemoryRecord(
                memory_id=memory_id,
                memory_kind=MemoryKind.REPOSITORY_FACT,
                statement="Repository uses Python.",
                normalized_statement="repository uses python",
                confidence=0.9,
                repository_scope=repository,
                evidence_references=("evidence-1",),
                source_references=("source-1",),
                applicability=MemoryApplicability(
                    kind=ApplicabilityKind.EXACT_REPOSITORY,
                    repository_scope=repository,
                    rationale="Repository scoped.",
                ),
                retention_class=RetentionClass.PROJECT_LIFETIME,
            )
        )

    result = retrieve_memory(
        storage=storage,
        query=MemoryQuery(
            query_id="query-1",
            repository_scope="repository-a",
            requested_by="Aerion",
        ),
        query_text="python repository",
        policy=AutonomousMemoryPolicy(),
    )

    assert tuple(
        record.memory_id
        for record in result.records
    ) == ("memory-1",)