import pytest
from pydantic import ValidationError

from forge.domain_intelligence.knowledge_loader.models import (
    KnowledgeChunk,
    KnowledgeFinding,
    KnowledgeFindingSeverity,
    KnowledgeLoadReport,
    KnowledgeManifest,
)


def test_knowledge_chunk_is_immutable() -> None:
    chunk = KnowledgeChunk(
        chunk_id="knowledge-chunk-1",
        document_id="knowledge-document-1",
        ordinal=0,
        text="Engineering knowledge.",
        token_estimate=4,
    )

    with pytest.raises(ValidationError):
        chunk.text = "Changed"


def test_knowledge_manifest_rejects_duplicate_ids() -> None:
    with pytest.raises(ValidationError):
        KnowledgeManifest(
            manifest_id="knowledge-manifest-1",
            project_root=".",
            source_ids=("source-1", "source-1"),
        )


def test_knowledge_report_rejects_duplicate_findings() -> None:
    manifest = KnowledgeManifest(
        manifest_id="knowledge-manifest-1",
        project_root=".",
    )
    finding = KnowledgeFinding(
        finding_id="knowledge-finding-1",
        category="compatibility",
        severity=KnowledgeFindingSeverity.MEDIUM,
        message="Unsupported schema version.",
    )

    with pytest.raises(ValidationError):
        KnowledgeLoadReport(
            report_id="knowledge-report-1",
            manifest=manifest,
            findings=(finding, finding),
        )