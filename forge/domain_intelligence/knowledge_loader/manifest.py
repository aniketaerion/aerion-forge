"""Knowledge manifest generation for M4.7 Package 1."""

from __future__ import annotations

from forge.domain_intelligence.knowledge_loader.identifiers import (
    knowledge_manifest_identifier,
)
from forge.domain_intelligence.knowledge_loader.models import (
    KnowledgeDocument,
    KnowledgeManifest,
    KnowledgeSource,
)


def build_knowledge_manifest(
    project_root: str,
    sources: tuple[KnowledgeSource, ...],
    documents: tuple[KnowledgeDocument, ...],
) -> KnowledgeManifest:
    source_ids = tuple(
        source.source_id for source in sources
    )
    document_ids = tuple(
        document.document_id for document in documents
    )

    payload = {
        "project_root": project_root,
        "source_ids": source_ids,
        "document_ids": document_ids,
    }

    return KnowledgeManifest(
        manifest_id=knowledge_manifest_identifier(payload),
        project_root=project_root,
        source_ids=source_ids,
        document_ids=document_ids,
    )