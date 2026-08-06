"""M4.7 Knowledge Loader Intelligence public API."""

from forge.domain_intelligence.knowledge_loader.errors import (
    KnowledgeCompatibilityError,
    KnowledgeLoaderConfigurationError,
    KnowledgeLoaderError,
    KnowledgeLoaderPolicyError,
    KnowledgeSourceError,
)
from forge.domain_intelligence.knowledge_loader.identifiers import (
    knowledge_chunk_identifier,
    knowledge_document_identifier,
    knowledge_finding_identifier,
    knowledge_manifest_identifier,
    knowledge_report_identifier,
    knowledge_source_identifier,
)
from forge.domain_intelligence.knowledge_loader.models import (
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeFinding,
    KnowledgeFindingSeverity,
    KnowledgeLoadReport,
    KnowledgeLoadRequest,
    KnowledgeLoadStatus,
    KnowledgeManifest,
    KnowledgeSource,
    KnowledgeSourceKind,
)
from forge.domain_intelligence.knowledge_loader.policies import (
    KnowledgeLoaderPolicy,
    is_allowed_knowledge_path,
    resolve_knowledge_repository_root,
    validate_knowledge_request,
)
from forge.domain_intelligence.knowledge_loader.reporting import (
    KnowledgeLoaderReportSummary,
    knowledge_loader_report_markdown,
    knowledge_loader_report_summary,
    write_knowledge_loader_report_bundle,
)

__all__ = [
    "KnowledgeChunk",
    "KnowledgeCompatibilityError",
    "KnowledgeDocument",
    "KnowledgeFinding",
    "KnowledgeFindingSeverity",
    "KnowledgeLoadReport",
    "KnowledgeLoadRequest",
    "KnowledgeLoadStatus",
    "KnowledgeLoaderConfigurationError",
    "KnowledgeLoaderError",
    "KnowledgeLoaderPolicy",
    "KnowledgeLoaderPolicyError",
    "KnowledgeLoaderReportSummary",
    "KnowledgeManifest",
    "KnowledgeSource",
    "KnowledgeSourceError",
    "KnowledgeSourceKind",
    "is_allowed_knowledge_path",
    "knowledge_chunk_identifier",
    "knowledge_document_identifier",
    "knowledge_finding_identifier",
    "knowledge_loader_report_markdown",
    "knowledge_loader_report_summary",
    "knowledge_manifest_identifier",
    "knowledge_report_identifier",
    "knowledge_source_identifier",
    "resolve_knowledge_repository_root",
    "validate_knowledge_request",
    "write_knowledge_loader_report_bundle",
]