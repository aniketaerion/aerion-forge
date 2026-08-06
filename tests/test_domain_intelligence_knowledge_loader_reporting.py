import json
from pathlib import Path

from forge.domain_intelligence.knowledge_loader.models import (
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeFinding,
    KnowledgeFindingSeverity,
    KnowledgeLoadReport,
    KnowledgeManifest,
    KnowledgeSource,
    KnowledgeSourceKind,
)
from forge.domain_intelligence.knowledge_loader.reporting import (
    knowledge_loader_report_markdown,
    knowledge_loader_report_summary,
    write_knowledge_loader_report_bundle,
)


def example_report() -> KnowledgeLoadReport:
    source = KnowledgeSource(
        source_id="knowledge-source-1",
        path="docs/guide.md",
        kind=KnowledgeSourceKind.MARKDOWN,
        size_bytes=100,
        content_hash="abc",
    )
    document = KnowledgeDocument(
        document_id="knowledge-document-1",
        source_id=source.source_id,
        title="Forge Guide",
        text="Knowledge loading.",
    )
    chunk = KnowledgeChunk(
        chunk_id="knowledge-chunk-1",
        document_id=document.document_id,
        ordinal=0,
        text="Knowledge loading.",
        token_estimate=2,
    )
    manifest = KnowledgeManifest(
        manifest_id="knowledge-manifest-1",
        project_root="docs",
        source_ids=(source.source_id,),
        document_ids=(document.document_id,),
        chunk_ids=(chunk.chunk_id,),
    )
    finding = KnowledgeFinding(
        finding_id="knowledge-finding-1",
        category="compatibility",
        severity=KnowledgeFindingSeverity.LOW,
        message="Compatibility review required.",
        path=source.path,
    )

    return KnowledgeLoadReport(
        report_id="knowledge-report-1",
        manifest=manifest,
        sources=(source,),
        documents=(document,),
        chunks=(chunk,),
        findings=(finding,),
    )


def test_knowledge_loader_report_summary() -> None:
    summary = knowledge_loader_report_summary(example_report())

    assert summary["source_count"] == 1
    assert summary["document_count"] == 1
    assert summary["chunk_count"] == 1
    assert summary["finding_count"] == 1
    assert summary["source_kind_counts"] == {
        "markdown": 1,
    }
    assert summary["finding_severity_counts"] == {
        "low": 1,
    }
    assert summary["total_source_bytes"] == 100
    assert summary["total_chunk_tokens"] == 2


def test_knowledge_loader_report_markdown() -> None:
    markdown = knowledge_loader_report_markdown(
        example_report()
    )

    assert "# Knowledge Loader Intelligence Report" in markdown
    assert "Forge Guide" in markdown
    assert "docs/guide.md" in markdown
    assert "compatibility" in markdown


def test_write_knowledge_loader_report_bundle(
    tmp_path: Path,
) -> None:
    paths = write_knowledge_loader_report_bundle(
        example_report(),
        tmp_path,
    )

    assert set(paths) == {
        "analysis_json",
        "summary_json",
        "analysis_markdown",
    }
    assert all(path.is_file() for path in paths.values())

    analysis = json.loads(
        paths["analysis_json"].read_text(encoding="utf-8")
    )
    summary = json.loads(
        paths["summary_json"].read_text(encoding="utf-8")
    )
    markdown = paths["analysis_markdown"].read_text(
        encoding="utf-8"
    )

    assert analysis["report_id"] == "knowledge-report-1"
    assert summary["source_count"] == 1
    assert "Knowledge Loader Intelligence Report" in markdown