"""Validation helpers for M4.7 Package 2."""

from __future__ import annotations

from forge.domain_intelligence.knowledge_loader.identifiers import (
    knowledge_finding_identifier,
)
from forge.domain_intelligence.knowledge_loader.models import (
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeFinding,
    KnowledgeFindingSeverity,
)


def validate_documents(
    documents: tuple[KnowledgeDocument, ...],
) -> tuple[KnowledgeFinding, ...]:
    findings: list[KnowledgeFinding] = []

    for document in documents:
        if not document.title.strip():
            payload = {
                "category": "missing-title",
                "document_id": document.document_id,
            }
            findings.append(
                KnowledgeFinding(
                    finding_id=knowledge_finding_identifier(payload),
                    category="missing-title",
                    severity=KnowledgeFindingSeverity.LOW,
                    message="Knowledge document has no title.",
                    path=document.metadata.get("path"),
                )
            )

    return tuple(findings)


def validate_chunks(
    chunks: tuple[KnowledgeChunk, ...],
) -> tuple[KnowledgeFinding, ...]:
    findings: list[KnowledgeFinding] = []

    ordinals_by_document: dict[str, list[int]] = {}

    for chunk in chunks:
        ordinals_by_document.setdefault(
            chunk.document_id,
            [],
        ).append(chunk.ordinal)

    for document_id, ordinals in sorted(
        ordinals_by_document.items()
    ):
        expected = list(range(len(ordinals)))
        actual = sorted(ordinals)

        if actual != expected:
            payload = {
                "category": "chunk-ordinal-gap",
                "document_id": document_id,
                "actual": tuple(actual),
            }
            findings.append(
                KnowledgeFinding(
                    finding_id=knowledge_finding_identifier(payload),
                    category="chunk-ordinal-gap",
                    severity=KnowledgeFindingSeverity.MEDIUM,
                    message=(
                        "Knowledge chunk ordinals are not contiguous."
                    ),
                )
            )

    return tuple(findings)