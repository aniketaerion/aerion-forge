from forge.autonomous_memory.models import (
    MemoryApplicability,
    MemoryRecord,
)
from forge.autonomous_memory.search import score_record
from forge.autonomous_memory.states import (
    ApplicabilityKind,
    MemoryKind,
    RetentionClass,
)


def test_search_scores_term_overlap() -> None:
    record = MemoryRecord(
        memory_id="memory-1",
        memory_kind=MemoryKind.HYPOTHESIS,
        statement="Repository uses Python.",
        normalized_statement="repository uses python",
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

    result = score_record(
        record,
        "python repository",
    )

    assert result.score == 1.0
    assert result.matched_terms == (
        "python",
        "repository",
    )