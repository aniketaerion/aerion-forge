from forge.domain_intelligence.knowledge_loader.manifest import (
    build_knowledge_manifest,
)
from forge.domain_intelligence.knowledge_loader.models import (
    KnowledgeDocument,
    KnowledgeSource,
    KnowledgeSourceKind,
)


def test_knowledge_manifest_generation() -> None:
    source = KnowledgeSource(
        source_id="knowledge-source-1",
        path="guide.md",
        kind=KnowledgeSourceKind.MARKDOWN,
        size_bytes=10,
        content_hash="abc",
    )
    document = KnowledgeDocument(
        document_id="knowledge-document-1",
        source_id=source.source_id,
        title="Guide",
        text="Text",
    )

    manifest = build_knowledge_manifest(
        ".",
        (source,),
        (document,),
    )

    assert manifest.source_ids == (source.source_id,)
    assert manifest.document_ids == (document.document_id,)