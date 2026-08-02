"""Frozen domain models for Milestone 2.4 Engineering Memory."""

from collections.abc import Mapping
from enum import StrEnum

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

SCHEMA_VERSION = "1.0"


class FrozenModel(BaseModel):
    """Immutable strict model."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        validate_default=True,
    )


class MemoryType(StrEnum):
    """Controlled engineering-memory classifications."""

    MISSION = "mission"
    TASK = "task"
    IMPACT_ASSESSMENT = "impact_assessment"
    DECISION = "decision"
    APPROVAL = "approval"
    VALIDATION_REQUIREMENT = "validation_requirement"
    ENGINEERING_PATTERN = "engineering_pattern"
    LESSON_LEARNED = "lesson_learned"
    ARTIFACT_LINEAGE = "artifact_lineage"
    RELEASE_EVIDENCE = "release_evidence"


class MemoryRelationshipType(StrEnum):
    """Controlled relationships between memory records."""

    PRODUCED_BY = "produced_by"
    DERIVED_FROM = "derived_from"
    SUPPORTS = "supports"
    SUPERSEDES = "supersedes"
    REFERENCES = "references"
    APPLIES_TO = "applies_to"
    VALIDATED_BY = "validated_by"
    APPROVED_BY = "approved_by"
    PART_OF = "part_of"


class MemoryConfidence(StrEnum):
    """Confidence attached to a verified memory record."""

    VERIFIED = "verified"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class MemoryRetentionPolicy(StrEnum):
    """Controlled retention classifications."""

    PERMANENT = "permanent"
    RELEASE_LIFETIME = "release_lifetime"
    PROJECT_LIFETIME = "project_lifetime"
    SUPERSEDED = "superseded"
    TEMPORARY = "temporary"


class MemoryEvidenceType(StrEnum):
    """Controlled evidence sources."""

    MISSION_PLAN = "mission_plan"
    TASK_SET = "task_set"
    IMPACT_ASSESSMENT = "impact_assessment"
    DECISION_REPORT = "decision_report"
    VALIDATION_REPORT = "validation_report"
    RELEASE_REPORT = "release_report"
    CONFIGURATION_SNAPSHOT = "configuration_snapshot"
    CAPABILITY_DEFINITION = "capability_definition"
    SOURCE_ARTIFACT = "source_artifact"
    OTHER_VERIFIED_ARTIFACT = "other_verified_artifact"


class MemoryValidationSeverity(StrEnum):
    """Validation-message severity."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class MemoryEvidence(FrozenModel):
    """One verified evidence reference."""

    evidence_id: str
    evidence_type: MemoryEvidenceType
    reference: str
    fingerprint: str
    description: str

    @field_validator(
        "evidence_id",
        "reference",
        "fingerprint",
        "description",
    )
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        normalized = value.strip()

        if not normalized:
            raise ValueError("Memory evidence fields cannot be blank.")

        return normalized


class MemoryRelationship(FrozenModel):
    """One directed relationship between memory records."""

    relationship_id: str
    relationship_type: MemoryRelationshipType
    source_memory_id: str
    target_memory_id: str
    rationale: str

    @field_validator(
        "relationship_id",
        "source_memory_id",
        "target_memory_id",
        "rationale",
    )
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        normalized = value.strip()

        if not normalized:
            raise ValueError("Memory relationship fields cannot be blank.")

        return normalized

    @model_validator(mode="after")
    def reject_self_relationship(self) -> "MemoryRelationship":
        if self.source_memory_id == self.target_memory_id:
            raise ValueError("A memory relationship cannot reference itself.")

        return self


class MemoryRecord(FrozenModel):
    """Canonical verified Engineering Memory record."""

    schema_version: str = SCHEMA_VERSION
    memory_id: str
    memory_fingerprint: str
    memory_type: MemoryType
    title: str
    summary: str
    rationale: str
    mission_ids: tuple[str, ...] = ()
    task_ids: tuple[str, ...] = ()
    assessment_ids: tuple[str, ...] = ()
    capability_ids: tuple[str, ...] = ()
    milestones: tuple[str, ...] = ()
    source_artifacts: tuple[str, ...] = ()
    evidence: tuple[MemoryEvidence, ...]
    relationships: tuple[MemoryRelationship, ...] = ()
    tags: tuple[str, ...] = ()
    confidence: MemoryConfidence
    retention_policy: MemoryRetentionPolicy
    created_from_fingerprints: Mapping[str, str] = Field(default_factory=dict)

    @field_validator(
        "memory_id",
        "memory_fingerprint",
        "title",
        "summary",
        "rationale",
    )
    @classmethod
    def reject_blank_identity_or_text(cls, value: str) -> str:
        normalized = value.strip()

        if not normalized:
            raise ValueError("Engineering Memory identity and text fields cannot be blank.")

        return normalized

    @field_validator(
        "mission_ids",
        "task_ids",
        "assessment_ids",
        "capability_ids",
        "milestones",
        "source_artifacts",
        "tags",
    )
    @classmethod
    def normalize_string_collections(
        cls,
        value: tuple[str, ...],
    ) -> tuple[str, ...]:
        return tuple(sorted({item.strip() for item in value if item.strip()}))

    @field_validator("evidence")
    @classmethod
    def normalize_evidence(
        cls,
        value: tuple[MemoryEvidence, ...],
    ) -> tuple[MemoryEvidence, ...]:
        return tuple(
            sorted(
                value,
                key=lambda item: item.evidence_id,
            )
        )

    @field_validator("relationships")
    @classmethod
    def normalize_relationships(
        cls,
        value: tuple[MemoryRelationship, ...],
    ) -> tuple[MemoryRelationship, ...]:
        return tuple(
            sorted(
                value,
                key=lambda item: item.relationship_id,
            )
        )

    @field_validator("created_from_fingerprints")
    @classmethod
    def normalize_fingerprints(
        cls,
        value: Mapping[str, str],
    ) -> Mapping[str, str]:
        normalized = {
            key.strip(): fingerprint.strip()
            for key, fingerprint in value.items()
            if key.strip() and fingerprint.strip()
        }

        return dict(sorted(normalized.items()))

    @model_validator(mode="after")
    def validate_record(self) -> "MemoryRecord":
        if not self.evidence:
            raise ValueError("An Engineering Memory record requires evidence.")

        evidence_ids = [item.evidence_id for item in self.evidence]

        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("Memory evidence IDs must be unique.")

        relationship_ids = [item.relationship_id for item in self.relationships]

        if len(relationship_ids) != len(set(relationship_ids)):
            raise ValueError("Memory relationship IDs must be unique.")

        for relationship in self.relationships:
            if relationship.source_memory_id != self.memory_id:
                raise ValueError(
                    "Every relationship must originate from the containing memory record."
                )

        has_lineage = any(
            (
                self.mission_ids,
                self.task_ids,
                self.assessment_ids,
                self.capability_ids,
                self.milestones,
                self.source_artifacts,
            )
        )

        if not has_lineage:
            raise ValueError("An Engineering Memory record requires lineage.")

        return self


class EngineeringMemoryStatistics(FrozenModel):
    """Aggregate Engineering Memory statistics."""

    record_count: int = Field(ge=0)
    relationship_count: int = Field(ge=0)
    evidence_count: int = Field(ge=0)
    mission_count: int = Field(ge=0)
    task_count: int = Field(ge=0)
    assessment_count: int = Field(ge=0)
    capability_count: int = Field(ge=0)
    permanent_record_count: int = Field(ge=0)


class EngineeringMemoryGeneration(FrozenModel):
    """Deterministic generation metadata."""

    schema_version: str = SCHEMA_VERSION
    generation_id: str
    previous_generation_id: str | None = None
    store_fingerprint: str
    record_count: int = Field(ge=0)
    relationship_count: int = Field(ge=0)
    evidence_count: int = Field(ge=0)

    @field_validator(
        "generation_id",
        "store_fingerprint",
    )
    @classmethod
    def reject_blank_identity(cls, value: str) -> str:
        normalized = value.strip()

        if not normalized:
            raise ValueError("Engineering Memory generation identity cannot be blank.")

        return normalized


class EngineeringMemoryStore(BaseModel):
    """Persisted Engineering Memory state."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    records: dict[str, MemoryRecord] = Field(default_factory=dict)
    history: dict[str, list[MemoryRecord]] = Field(default_factory=dict)
    generation: EngineeringMemoryGeneration | None = None


class EngineeringMemoryConfiguration(FrozenModel):
    """Canonical Milestone 2.4 configuration."""

    enabled: bool = True
    strict: bool = True
    history_limit: int = Field(
        default=5,
        ge=0,
        le=100,
    )
    max_records: int = Field(
        default=10000,
        ge=1,
        le=1000000,
    )
    max_relationships_per_record: int = Field(
        default=250,
        ge=0,
        le=10000,
    )
    max_evidence_per_record: int = Field(
        default=250,
        ge=1,
        le=10000,
    )
    require_verified_evidence: bool = True
    allow_unknown_confidence: bool = False
    allow_temporary_records: bool = True


class EngineeringMemoryValidationMessage(FrozenModel):
    """One Engineering Memory validation message."""

    severity: MemoryValidationSeverity
    field: str
    message: str
    memory_id: str | None = None

    @field_validator("field", "message")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        normalized = value.strip()

        if not normalized:
            raise ValueError("Validation message fields cannot be blank.")

        return normalized


class EngineeringMemoryValidationResult(FrozenModel):
    """Aggregate Engineering Memory validation result."""

    valid: bool
    messages: tuple[
        EngineeringMemoryValidationMessage,
        ...,
    ] = ()


class EngineeringMemoryResult(FrozenModel):
    """Engineering Memory operation result."""

    records: tuple[MemoryRecord, ...]
    generation: EngineeringMemoryGeneration
    statistics: EngineeringMemoryStatistics
    report_paths: tuple[str, ...] = ()
