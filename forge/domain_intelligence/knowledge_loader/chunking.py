"""Knowledge document chunking for M4.7 Package 2."""

from __future__ import annotations

from forge.domain_intelligence.knowledge_loader.identifiers import (
    knowledge_chunk_identifier,
)
from forge.domain_intelligence.knowledge_loader.models import (
    KnowledgeChunk,
    KnowledgeDocument,
)


def _token_estimate(text: str) -> int:
    return max(1, len(text.split()))


def chunk_document(
    document: KnowledgeDocument,
    *,
    chunk_size: int,
) -> tuple[KnowledgeChunk, ...]:
    text = document.text.strip()
    if not text:
        return ()

    chunks: list[KnowledgeChunk] = []

    for ordinal, start in enumerate(range(0, len(text), chunk_size)):
        chunk_text = text[start : start + chunk_size].strip()
        if not chunk_text:
            continue

        payload = {
            "document_id": document.document_id,
            "ordinal": ordinal,
            "text": chunk_text,
        }

        chunks.append(
            KnowledgeChunk(
                chunk_id=knowledge_chunk_identifier(payload),
                document_id=document.document_id,
                ordinal=ordinal,
                text=chunk_text,
                token_estimate=_token_estimate(chunk_text),
                metadata={
                    "source_id": document.source_id,
                    **document.metadata,
                },
            )
        )

    return tuple(chunks)


def chunk_documents(
    documents: tuple[KnowledgeDocument, ...],
    *,
    chunk_size: int,
) -> tuple[KnowledgeChunk, ...]:
    return tuple(
        chunk
        for document in documents
        for chunk in chunk_document(
            document,
            chunk_size=chunk_size,
        )
    )