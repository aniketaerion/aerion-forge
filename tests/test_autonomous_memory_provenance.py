from forge.autonomous_memory.models import MemoryObservation
from forge.autonomous_memory.provenance import (
    build_provenance,
    evidence_digest,
)
from forge.autonomous_memory.states import MemorySourceKind


def observation() -> MemoryObservation:
    return MemoryObservation(
        observation_id="observation-1",
        source_kind=MemorySourceKind.REPOSITORY,
        source_reference="forge/module.py",
        repository_root="repository",
        repository_fingerprint="fingerprint-1",
        content="Repository fact.",
        evidence_references=("evidence-2", "evidence-1"),
    )


def test_digest_is_order_independent() -> None:
    assert evidence_digest(
        ("evidence-1", "evidence-2")
    ) == evidence_digest(
        ("evidence-2", "evidence-1")
    )


def test_provenance_is_created() -> None:
    result = build_provenance(
        memory_id="memory-1",
        observation=observation(),
        actor="Aerion",
    )
    assert result.memory_id == "memory-1"