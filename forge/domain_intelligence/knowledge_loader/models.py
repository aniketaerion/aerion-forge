"""Immutable contracts for M4.7 Knowledge Loader Intelligence."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class KnowledgeSourceKind(StrEnum):
    MARKDOWN = "markdown"
    TEXT = "text"
    JSON = "json"
    YAML = "yaml"
    TOML = "toml"
    PYTHON = "python"
    DOCUMENTATION = "documentation"
    MANIFEST = "manifest"
    UNKNOWN = "unknown"


class KnowledgeLoadStatus(StrEnum):
    DISCOVERED = "discovered"
    LOADED = "loaded"
    SKIPPED = "skipped"
    REJECTED = "rejected"
    FAILED = "failed"


class KnowledgeFindingSeverity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ImmutableKnowledgeModel(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        str_strip_whitespace=True,
    )


class KnowledgeLoadRequest(ImmutableKnowledgeModel):
    repository_root: str = Field(min_length=1)
    project_root: str = Field(default=".", min_length=1)
    include_patterns: tuple[str, ...] = ()
    exclude_patterns: tuple[str, ...] = ()
    max_files: int = Field(default=5000, ge=1, le=100000)
    max_file_bytes: int = Field(
        default=2_000_000,
        ge=1,
        le=100_000_000,
    )
    chunk_size: int = Field(default=4000, ge=128, le=50000)


class KnowledgeSource(ImmutableKnowledgeModel):
    source_id: str = Field(min_length=1)
    path: str = Field(min_length=1)
    kind: KnowledgeSourceKind
    size_bytes: int = Field(ge=0)
    content_hash: str = Field(min_length=1)
    encoding: str = Field(default="utf-8", min_length=1)
    status: KnowledgeLoadStatus = KnowledgeLoadStatus.DISCOVERED


class KnowledgeDocument(ImmutableKnowledgeModel):
    document_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    text: str
    metadata: dict[str, str] = Field(default_factory=dict)


class KnowledgeChunk(ImmutableKnowledgeModel):
    chunk_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    ordinal: int = Field(ge=0)
    text: str = Field(min_length=1)
    token_estimate: int = Field(ge=1)
    metadata: dict[str, str] = Field(default_factory=dict)


class KnowledgeManifest(ImmutableKnowledgeModel):
    manifest_id: str = Field(min_length=1)
    project_root: str = Field(min_length=1)
    source_ids: tuple[str, ...] = ()
    document_ids: tuple[str, ...] = ()
    chunk_ids: tuple[str, ...] = ()
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )

    @field_validator(
        "source_ids",
        "document_ids",
        "chunk_ids",
    )
    @classmethod
    def ensure_unique_identifiers(
        cls,
        identifiers: tuple[str, ...],
    ) -> tuple[str, ...]:
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("knowledge identifiers must be unique")
        return identifiers


class KnowledgeFinding(ImmutableKnowledgeModel):
    finding_id: str = Field(min_length=1)
    category: str = Field(min_length=1)
    severity: KnowledgeFindingSeverity
    message: str = Field(min_length=1)
    path: str | None = None
    evidence: dict[str, str] = Field(default_factory=dict)


class KnowledgeLoadReport(ImmutableKnowledgeModel):
    report_id: str = Field(min_length=1)
    manifest: KnowledgeManifest
    sources: tuple[KnowledgeSource, ...] = ()
    documents: tuple[KnowledgeDocument, ...] = ()
    chunks: tuple[KnowledgeChunk, ...] = ()
    findings: tuple[KnowledgeFinding, ...] = ()
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )

    @field_validator("findings")
    @classmethod
    def ensure_unique_findings(
        cls,
        findings: tuple[KnowledgeFinding, ...],
    ) -> tuple[KnowledgeFinding, ...]:
        identifiers = [finding.finding_id for finding in findings]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError(
                "knowledge finding identifiers must be unique"
            )
        return findings