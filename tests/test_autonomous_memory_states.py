from forge.autonomous_memory.states import (
    ApplicabilityKind,
    MemoryKind,
    MemoryStatus,
)


def test_memory_enumerations_are_stable() -> None:
    assert MemoryKind.REPOSITORY_FACT.value == "repository_fact"
    assert MemoryStatus.SUPERSEDED.value == "superseded"
    assert (
        ApplicabilityKind.EXACT_REPOSITORY.value
        == "exact_repository"
    )