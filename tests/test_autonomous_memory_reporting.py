import json

from forge.autonomous_memory.models import (
    MemoryApplicability,
    MemoryRecord,
)
from forge.autonomous_memory.reporting import (
    MemoryReport,
    memory_report_json,
    memory_report_markdown,
)
from forge.autonomous_memory.states import (
    ApplicabilityKind,
    MemoryKind,
    RetentionClass,
)


def record() -> MemoryRecord:
    return MemoryRecord(
        memory_id="memory-1",
        memory_kind=MemoryKind.REPOSITORY_FACT,
        statement="Repository uses Python.",
        normalized_statement="repository uses python",
        confidence=0.9,
        repository_scope="repository",
        evidence_references=("evidence-1",),
        source_references=("source-1",),
        applicability=MemoryApplicability(
            kind=ApplicabilityKind.EXACT_REPOSITORY,
            repository_scope="repository",
            rationale="Repository scoped.",
        ),
        retention_class=RetentionClass.PROJECT_LIFETIME,
    )


def test_json_report_is_serializable() -> None:
    payload = json.loads(
        memory_report_json(
            MemoryReport(
                records=(record(),),
                matches=(),
                learning=(),
            )
        )
    )

    assert payload["record_count"] == 1
    assert payload["records"][0]["memory_id"] == "memory-1"


def test_markdown_report_contains_record() -> None:
    markdown = memory_report_markdown(
        MemoryReport(
            records=(record(),),
            matches=(),
            learning=(),
        )
    )

    assert "# Autonomous Memory Report" in markdown
    assert "memory-1" in markdown