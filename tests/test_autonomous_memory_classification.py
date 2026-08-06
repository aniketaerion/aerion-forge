from forge.autonomous_memory.classification import classify_observation
from forge.autonomous_memory.models import MemoryObservation
from forge.autonomous_memory.states import (
    MemoryKind,
    MemorySourceKind,
)


def make_observation(
    content: str,
    evidence: tuple[str, ...] = (),
) -> MemoryObservation:
    return MemoryObservation(
        observation_id="observation-1",
        source_kind=MemorySourceKind.REPOSITORY,
        source_reference="source-1",
        repository_root="repository",
        repository_fingerprint="fingerprint-1",
        content=content,
        evidence_references=evidence,
    )


def test_failure_is_classified() -> None:
    result = classify_observation(
        make_observation("Validation failed after deployment.")
    )
    assert result.memory_kind is MemoryKind.FAILURE_PATTERN


def test_evidence_backed_default_is_fact() -> None:
    result = classify_observation(
        make_observation(
            "Repository uses Python.",
            ("evidence-1",),
        )
    )
    assert result.memory_kind is MemoryKind.REPOSITORY_FACT