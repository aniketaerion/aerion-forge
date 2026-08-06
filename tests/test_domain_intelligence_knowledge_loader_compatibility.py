from forge.domain_intelligence.knowledge_loader.compatibility import (
    analyze_knowledge_compatibility,
)
from forge.domain_intelligence.knowledge_loader.models import (
    KnowledgeDocument,
    KnowledgeSource,
    KnowledgeSourceKind,
)


def test_compatibility_detects_missing_document() -> None:
    source = KnowledgeSource(
        source_id="source-1",
        path="guide.md",
        kind=KnowledgeSourceKind.MARKDOWN,
        size_bytes=10,
        content_hash="abc",
    )

    findings = analyze_knowledge_compatibility(
        (source,),
        (),
    )

    assert findings[0].category == "missing-document"


def test_compatibility_detects_empty_document() -> None:
    source = KnowledgeSource(
        source_id="source-1",
        path="guide.md",
        kind=KnowledgeSourceKind.MARKDOWN,
        size_bytes=0,
        content_hash="abc",
    )
    document = KnowledgeDocument(
        document_id="document-1",
        source_id=source.source_id,
        title="Guide",
        text="",
    )

    findings = analyze_knowledge_compatibility(
        (source,),
        (document,),
    )

    assert findings[0].category == "empty-document"