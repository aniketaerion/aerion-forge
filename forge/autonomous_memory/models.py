"""Immutable contracts for autonomous memory and learning."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from forge.autonomous_memory.states import (
    ApplicabilityKind,
    MemoryKind,
    MemorySourceKind,
    MemoryStatus,
    RetentionClass,
)


def utc_now() -> datetime:
    return datetime.now(UTC)


class FrozenMemoryContract(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class MemoryObservation(FrozenMemoryContract):
    observation_id: str = Field(min_length=1)
    schema_version: str = "1.0"
    source_kind: MemorySourceKind
    source_reference: str = Field(min_length=1)
    repository_root: str = Field(min_length=1)
    repository_fingerprint: str = Field(min_length=1)
    mission_id: str | None = None
    session_id: str | None = None
    content: str = Field(min_length=1, max_length=500000)
    evidence_references: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    observed_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_collections(self) -> MemoryObservation:
        if len(set(self.evidence_references)) != len(
            self.evidence_references
        ):
            raise ValueError(
                "evidence_references cannot contain duplicates."
            )
        if len(set(self.tags)) != len(self.tags):
            raise ValueError("tags cannot contain duplicates.")
        return self


class MemoryApplicability(FrozenMemoryContract):
    kind: ApplicabilityKind
    repository_scope: str = Field(min_length=1)
    module_scope: tuple[str, ...] = ()
    capability_scope: tuple[str, ...] = ()
    business_domain: str | None = None
    rationale: str = Field(min_length=1)


class MemoryRecord(FrozenMemoryContract):
    memory_id: str = Field(min_length=1)
    schema_version: str = "1.0"
    memory_kind: MemoryKind
    statement: str = Field(min_length=1)
    normalized_statement: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    repository_scope: str = Field(min_length=1)
    module_scope: tuple[str, ...] = ()
    capability_scope: tuple[str, ...] = ()
    business_domain: str | None = None
    evidence_references: tuple[str, ...] = ()
    source_references: tuple[str, ...] = Field(min_length=1)
    tags: tuple[str, ...] = ()
    applicability: MemoryApplicability
    retention_class: RetentionClass
    status: MemoryStatus = MemoryStatus.ACTIVE
    supersedes_memory_id: str | None = None
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_record(self) -> MemoryRecord:
        fact_like = {
            MemoryKind.REPOSITORY_FACT,
            MemoryKind.ARCHITECTURE_CONSTRAINT,
            MemoryKind.BUSINESS_RULE,
        }

        if (
            self.memory_kind in fact_like
            and not self.evidence_references
        ):
            raise ValueError(
                "Fact-like memory requires evidence."
            )

        if self.supersedes_memory_id == self.memory_id:
            raise ValueError(
                "Memory cannot supersede itself."
            )

        return self


class MemoryProvenance(FrozenMemoryContract):
    provenance_id: str = Field(min_length=1)
    memory_id: str = Field(min_length=1)
    source_kind: MemorySourceKind
    source_reference: str = Field(min_length=1)
    evidence_digest: str = Field(min_length=1)
    repository_fingerprint: str = Field(min_length=1)
    actor: str = Field(min_length=1)
    captured_at: datetime = Field(default_factory=utc_now)


class MemoryQuery(FrozenMemoryContract):
    query_id: str = Field(min_length=1)
    repository_scope: str = Field(min_length=1)
    module_scope: tuple[str, ...] = ()
    capability_scope: tuple[str, ...] = ()
    business_domain: str | None = None
    memory_kinds: tuple[MemoryKind, ...] = ()
    tags: tuple[str, ...] = ()
    minimum_confidence: float = Field(
        default=0.40,
        ge=0.0,
        le=1.0,
    )
    maximum_results: int = Field(default=20, ge=1, le=200)
    include_superseded: bool = False
    requested_by: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=utc_now)


class MemoryMatch(FrozenMemoryContract):
    memory_id: str = Field(min_length=1)
    relevance_score: float = Field(ge=0.0, le=1.0)
    confidence_score: float = Field(ge=0.0, le=1.0)
    recency_score: float = Field(ge=0.0, le=1.0)
    applicability_score: float = Field(ge=0.0, le=1.0)
    total_score: float
    matched_terms: tuple[str, ...] = ()
    rationale: str = Field(min_length=1)


class LearningRecord(FrozenMemoryContract):
    learning_id: str = Field(min_length=1)
    source_memory_ids: tuple[str, ...] = Field(min_length=1)
    lesson: str = Field(min_length=1)
    success_count: int = Field(default=0, ge=0)
    failure_count: int = Field(default=0, ge=0)
    confidence: float = Field(ge=0.0, le=1.0)
    applicability: MemoryApplicability
    last_validated_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_sources(self) -> LearningRecord:
        if len(set(self.source_memory_ids)) != len(
            self.source_memory_ids
        ):
            raise ValueError(
                "source_memory_ids cannot contain duplicates."
            )
        return self