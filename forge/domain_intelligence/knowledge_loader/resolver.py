"""Knowledge path and document resolution for M4.7 Package 1."""

from __future__ import annotations

from pathlib import Path

from forge.domain_intelligence.knowledge_loader.errors import (
    KnowledgeLoaderPolicyError,
)
from forge.domain_intelligence.knowledge_loader.models import (
    KnowledgeDocument,
    KnowledgeSource,
)


def resolve_knowledge_project_root(
    repository_root: Path,
    project_root: str,
) -> Path:
    resolved = (repository_root / project_root).resolve()

    try:
        resolved.relative_to(repository_root.resolve())
    except ValueError as exc:
        raise KnowledgeLoaderPolicyError(
            "knowledge project root escapes repository"
        ) from exc

    if not resolved.is_dir():
        raise KnowledgeLoaderPolicyError(
            f"knowledge project root does not exist: {resolved}"
        )

    return resolved


def source_by_id(
    sources: tuple[KnowledgeSource, ...],
    source_id: str,
) -> KnowledgeSource | None:
    return next(
        (
            source
            for source in sources
            if source.source_id == source_id
        ),
        None,
    )


def document_by_id(
    documents: tuple[KnowledgeDocument, ...],
    document_id: str,
) -> KnowledgeDocument | None:
    return next(
        (
            document
            for document in documents
            if document.document_id == document_id
        ),
        None,
    )