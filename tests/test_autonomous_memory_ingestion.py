import pytest

from forge.autonomous_memory.errors import MemoryRedactionError
from forge.autonomous_memory.ingestion import MemoryIngestionService
from forge.autonomous_memory.models import MemoryObservation
from forge.autonomous_memory.policies import AutonomousMemoryPolicy
from forge.autonomous_memory.states import (
    MemoryKind,
    MemorySourceKind,
)


def observation(
    content: str,
    evidence: tuple[str, ...] = ("evidence-1",),
) -> MemoryObservation:
    return MemoryObservation(
        observation_id="observation-1",
        source_kind=MemorySourceKind.REPOSITORY,
        source_reference="forge/module.py",
        repository_root="repository",
        repository_fingerprint="fingerprint-1",
        content=content,
        evidence_references=evidence,
        tags=("Architecture", "architecture"),
    )


def test_ingestion_creates_record_and_provenance() -> None:
    service = MemoryIngestionService(
        policy=AutonomousMemoryPolicy()
    )
    result = service.ingest(
        observation("Repository uses Python."),
        actor="Aerion",
        module_scope=("forge\\module.py",),
    )
    assert result.record.memory_kind is MemoryKind.REPOSITORY_FACT
    assert result.record.module_scope == ("forge/module.py",)
    assert result.record.tags == ("architecture",)
    assert result.provenance.memory_id == result.record.memory_id


def test_without_evidence_remains_hypothesis() -> None:
    service = MemoryIngestionService(
        policy=AutonomousMemoryPolicy()
    )
    result = service.ingest(
        observation("Repository may use another runtime.", ()),
        actor="Aerion",
    )
    assert result.record.memory_kind is MemoryKind.HYPOTHESIS


def test_ingestion_rejects_secret() -> None:
    service = MemoryIngestionService(
        policy=AutonomousMemoryPolicy()
    )
    with pytest.raises(MemoryRedactionError):
        service.ingest(
            observation("api_key=abcdefghijklmnop"),
            actor="Aerion",
        )