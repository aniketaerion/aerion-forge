import pytest
from pydantic import ValidationError

from forge.autonomous_memory.models import (
    LearningRecord,
    MemoryApplicability,
    MemoryObservation,
    MemoryRecord,
)
from forge.autonomous_memory.states import (
    ApplicabilityKind,
    MemoryKind,
    MemorySourceKind,
    RetentionClass,
)


def applicability() -> MemoryApplicability:
    return MemoryApplicability(
        kind=ApplicabilityKind.EXACT_REPOSITORY,
        repository_scope="repository",
        rationale="Repository-scoped memory.",
    )


def test_fact_requires_evidence() -> None:
    with pytest.raises(ValidationError):
        MemoryRecord(
            memory_id="memory-1",
            memory_kind=MemoryKind.REPOSITORY_FACT,
            statement="Repository uses Python.",
            normalized_statement="repository uses python",
            confidence=0.9,
            repository_scope="repository",
            source_references=("source-1",),
            applicability=applicability(),
            retention_class=RetentionClass.PROJECT_LIFETIME,
        )


def test_memory_cannot_supersede_itself() -> None:
    with pytest.raises(ValidationError):
        MemoryRecord(
            memory_id="memory-1",
            memory_kind=MemoryKind.HYPOTHESIS,
            statement="Possible constraint.",
            normalized_statement="possible constraint",
            confidence=0.5,
            repository_scope="repository",
            source_references=("source-1",),
            applicability=applicability(),
            retention_class=RetentionClass.TEMPORARY,
            supersedes_memory_id="memory-1",
        )


def test_observation_rejects_duplicate_evidence() -> None:
    with pytest.raises(ValidationError):
        MemoryObservation(
            observation_id="observation-1",
            source_kind=MemorySourceKind.REPOSITORY,
            source_reference="file.py",
            repository_root="repository",
            repository_fingerprint="fingerprint-1",
            content="Observed repository fact.",
            evidence_references=("evidence-1", "evidence-1"),
        )


def test_learning_requires_unique_sources() -> None:
    with pytest.raises(ValidationError):
        LearningRecord(
            learning_id="learning-1",
            source_memory_ids=("memory-1", "memory-1"),
            lesson="Use validated rollback checkpoints.",
            confidence=0.8,
            applicability=applicability(),
        )