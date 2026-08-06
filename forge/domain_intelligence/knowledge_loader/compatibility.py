"""Compatibility analysis for M4.7 Package 2."""

from __future__ import annotations

from forge.domain_intelligence.knowledge_loader.identifiers import (
    knowledge_finding_identifier,
)
from forge.domain_intelligence.knowledge_loader.models import (
    KnowledgeDocument,
    KnowledgeFinding,
    KnowledgeFindingSeverity,
    KnowledgeSource,
    KnowledgeSourceKind,
)


def analyze_knowledge_compatibility(
    sources: tuple[KnowledgeSource, ...],
    documents: tuple[KnowledgeDocument, ...],
) -> tuple[KnowledgeFinding, ...]:
    findings: list[KnowledgeFinding] = []
    documents_by_source = {
        document.source_id: document
        for document in documents
    }

    for source in sources:
        document = documents_by_source.get(source.source_id)

        if document is None:
            payload = {
                "category": "missing-document",
                "path": source.path,
            }
            findings.append(
                KnowledgeFinding(
                    finding_id=knowledge_finding_identifier(payload),
                    category="missing-document",
                    severity=KnowledgeFindingSeverity.HIGH,
                    message="Discovered source has no loaded document.",
                    path=source.path,
                )
            )
            continue

        if source.kind is KnowledgeSourceKind.UNKNOWN:
            payload = {
                "category": "unknown-source-kind",
                "path": source.path,
            }
            findings.append(
                KnowledgeFinding(
                    finding_id=knowledge_finding_identifier(payload),
                    category="unknown-source-kind",
                    severity=KnowledgeFindingSeverity.LOW,
                    message="Knowledge source kind is unknown.",
                    path=source.path,
                )
            )

        if not document.text.strip():
            payload = {
                "category": "empty-document",
                "path": source.path,
            }
            findings.append(
                KnowledgeFinding(
                    finding_id=knowledge_finding_identifier(payload),
                    category="empty-document",
                    severity=KnowledgeFindingSeverity.MEDIUM,
                    message="Knowledge document is empty.",
                    path=source.path,
                )
            )

    return tuple(
        sorted(
            findings,
            key=lambda finding: (
                finding.severity.value,
                finding.category,
                finding.path or "",
            ),
        )
    )