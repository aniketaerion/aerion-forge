"""Knowledge loading service for M4.7 Package 1."""

from __future__ import annotations

from forge.domain_intelligence.knowledge_loader.chunking import (
    chunk_documents,
)
from forge.domain_intelligence.knowledge_loader.compatibility import (
    analyze_knowledge_compatibility,
)
from forge.domain_intelligence.knowledge_loader.discovery import (
    discover_knowledge_sources,
)
from forge.domain_intelligence.knowledge_loader.identifiers import (
    knowledge_report_identifier,
)
from forge.domain_intelligence.knowledge_loader.manifest import (
    build_knowledge_manifest,
)
from forge.domain_intelligence.knowledge_loader.models import (
    KnowledgeLoadReport,
    KnowledgeLoadRequest,
)
from forge.domain_intelligence.knowledge_loader.policies import (
    KnowledgeLoaderPolicy,
    resolve_knowledge_repository_root,
    validate_knowledge_request,
)
from forge.domain_intelligence.knowledge_loader.registry import (
    KnowledgeLoaderRegistry,
)
from forge.domain_intelligence.knowledge_loader.resolver import (
    resolve_knowledge_project_root,
)
from forge.domain_intelligence.knowledge_loader.validation import (
    validate_chunks,
    validate_documents,
)


class KnowledgeLoaderService:
    """Discover and load repository knowledge deterministically."""

    def __init__(
        self,
        *,
        policy: KnowledgeLoaderPolicy | None = None,
        registry: KnowledgeLoaderRegistry | None = None,
    ) -> None:
        self._policy = policy or KnowledgeLoaderPolicy()
        self._registry = (
            registry or KnowledgeLoaderRegistry.default()
        )

    def load(
        self,
        request: KnowledgeLoadRequest,
    ) -> KnowledgeLoadReport:
        validate_knowledge_request(request, self._policy)

        repository_root = resolve_knowledge_repository_root(
            request.repository_root,
            self._policy,
        )
        project_root = resolve_knowledge_project_root(
            repository_root,
            request.project_root,
        )

        sources = discover_knowledge_sources(
            project_root,
            self._policy,
            max_files=request.max_files,
        )
        documents = tuple(
            self._registry.load(project_root, source)
            for source in sources
        )

        relative_root = project_root.relative_to(
            repository_root
        ).as_posix()

        chunks = chunk_documents(
            documents,
            chunk_size=request.chunk_size,
        )

        manifest = build_knowledge_manifest(
            relative_root,
            sources,
            documents,
        ).model_copy(
            update={
                "chunk_ids": tuple(
                    chunk.chunk_id for chunk in chunks
                )
            }
        )

        findings = (
            *analyze_knowledge_compatibility(
                sources,
                documents,
            ),
            *validate_documents(documents),
            *validate_chunks(chunks),
        )

        payload = {
            "manifest_id": manifest.manifest_id,
            "source_ids": manifest.source_ids,
            "document_ids": manifest.document_ids,
            "chunk_ids": manifest.chunk_ids,
            "finding_ids": tuple(
                finding.finding_id for finding in findings
            ),
        }

        return KnowledgeLoadReport(
            report_id=knowledge_report_identifier(payload),
            manifest=manifest,
            sources=sources,
            documents=documents,
            chunks=chunks,
            findings=findings,
        )