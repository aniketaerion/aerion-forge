"""Mission Reporting domain models."""

from collections.abc import Mapping
from enum import StrEnum
from types import MappingProxyType
from typing import Annotated, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, field_validator, model_validator

SCHEMA_VERSION = "1.0"


def _serialize_string_mapping(
    value: Mapping[str, str],
) -> dict[str, str]:
    """Serialize an immutable mapping as canonical JSON data."""

    return {key: value[key] for key in sorted(value)}


SerializableStringMapping: TypeAlias = Annotated[
    Mapping[str, str],
    PlainSerializer(
        _serialize_string_mapping,
        return_type=dict[str, str],
        when_used="always",
    ),
]


class FrozenModel(BaseModel):
    """Immutable validated model."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )


class MissionReportStatus(StrEnum):
    """Derived mission-report readiness state."""

    READY = "ready"
    CONDITIONAL = "conditional"
    BLOCKED = "blocked"


class MissionReportSectionType(StrEnum):
    """Supported mission-report section types."""

    EXECUTIVE_SUMMARY = "executive_summary"
    MISSION = "mission"
    TASKS = "tasks"
    IMPACT = "impact"
    ENGINEERING_MEMORY = "engineering_memory"
    RISKS = "risks"
    TRACEABILITY = "traceability"
    VALIDATION = "validation"


class MissionReportRiskSeverity(StrEnum):
    """Mission-report risk severity."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MissionReportingValidationSeverity(StrEnum):
    """Validation message severity."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class MissionReportRisk(FrozenModel):
    """One normalized mission-report risk."""

    risk_id: str
    title: str
    description: str
    severity: MissionReportRiskSeverity
    source_type: str
    source_id: str
    affected_task_ids: tuple[str, ...] = ()
    mitigation: str | None = None

    @field_validator(
        "risk_id",
        "title",
        "description",
        "source_type",
        "source_id",
    )
    @classmethod
    def validate_required_text(
        cls,
        value: str,
    ) -> str:
        normalized = value.strip()

        if not normalized:
            raise ValueError("Value cannot be blank.")

        return normalized

    @field_validator("affected_task_ids")
    @classmethod
    def normalize_task_ids(
        cls,
        value: tuple[str, ...],
    ) -> tuple[str, ...]:
        return tuple(sorted({item.strip() for item in value if item.strip()}))


class MissionTraceabilityItem(FrozenModel):
    """One traceability relationship in a mission report."""

    traceability_id: str
    source_type: str
    source_id: str
    target_type: str
    target_id: str
    relationship: str
    evidence_ids: tuple[str, ...] = ()

    @field_validator(
        "traceability_id",
        "source_type",
        "source_id",
        "target_type",
        "target_id",
        "relationship",
    )
    @classmethod
    def validate_required_text(
        cls,
        value: str,
    ) -> str:
        normalized = value.strip()

        if not normalized:
            raise ValueError("Value cannot be blank.")

        return normalized

    @field_validator("evidence_ids")
    @classmethod
    def normalize_evidence_ids(
        cls,
        value: tuple[str, ...],
    ) -> tuple[str, ...]:
        return tuple(sorted({item.strip() for item in value if item.strip()}))


class MissionReportSection(FrozenModel):
    """One deterministic report section."""

    section_id: str
    section_type: MissionReportSectionType
    title: str
    summary: str
    content: tuple[str, ...] = ()
    source_ids: tuple[str, ...] = ()

    @field_validator(
        "section_id",
        "title",
        "summary",
    )
    @classmethod
    def validate_required_text(
        cls,
        value: str,
    ) -> str:
        normalized = value.strip()

        if not normalized:
            raise ValueError("Value cannot be blank.")

        return normalized

    @field_validator("content", "source_ids")
    @classmethod
    def normalize_collections(
        cls,
        value: tuple[str, ...],
    ) -> tuple[str, ...]:
        return tuple(item.strip() for item in value if item.strip())


class MissionReportStatistics(FrozenModel):
    """Aggregate mission-report statistics."""

    task_count: int = Field(ge=0)
    blocked_task_count: int = Field(ge=0)
    risk_count: int = Field(ge=0)
    high_risk_count: int = Field(ge=0)
    critical_risk_count: int = Field(ge=0)
    traceability_count: int = Field(ge=0)
    section_count: int = Field(ge=0)
    engineering_memory_record_count: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_aggregates(self) -> "MissionReportStatistics":
        if self.blocked_task_count > self.task_count:
            raise ValueError("Blocked task count cannot exceed total task count.")

        if self.high_risk_count > self.risk_count:
            raise ValueError("High-risk count cannot exceed total risk count.")

        if self.critical_risk_count > self.risk_count:
            raise ValueError("Critical-risk count cannot exceed total risk count.")

        return self


class MissionReport(FrozenModel):
    """Canonical deterministic Mission Report."""

    schema_version: str = SCHEMA_VERSION
    report_id: str
    mission_id: str
    mission_fingerprint: str
    task_set_fingerprint: str
    assessment_id: str
    assessment_fingerprint: str
    engineering_memory_generation_id: str
    title: str
    executive_summary: str
    status: MissionReportStatus
    sections: tuple[MissionReportSection, ...]
    risks: tuple[MissionReportRisk, ...] = ()
    traceability: tuple[MissionTraceabilityItem, ...] = ()
    statistics: MissionReportStatistics
    source_fingerprints: SerializableStringMapping
    report_fingerprint: str

    @field_validator(
        "report_id",
        "mission_id",
        "mission_fingerprint",
        "task_set_fingerprint",
        "assessment_id",
        "assessment_fingerprint",
        "engineering_memory_generation_id",
        "title",
        "executive_summary",
        "report_fingerprint",
    )
    @classmethod
    def validate_required_text(
        cls,
        value: str,
    ) -> str:
        normalized = value.strip()

        if not normalized:
            raise ValueError("Value cannot be blank.")

        return normalized

    @field_validator("source_fingerprints", mode="after")
    @classmethod
    def normalize_source_fingerprints(
        cls,
        value: Mapping[str, str],
    ) -> Mapping[str, str]:
        normalized = {
            str(key).strip(): str(item).strip()
            for key, item in value.items()
            if str(key).strip() and str(item).strip()
        }

        return MappingProxyType({key: normalized[key] for key in sorted(normalized)})

    @model_validator(mode="after")
    def validate_statistics(self) -> "MissionReport":
        if self.statistics.section_count != len(self.sections):
            raise ValueError("Section count does not match report sections.")

        if self.statistics.risk_count != len(self.risks):
            raise ValueError("Risk count does not match report risks.")

        if self.statistics.traceability_count != len(self.traceability):
            raise ValueError("Traceability count does not match report traceability.")

        return self


class MissionReportingConfiguration(FrozenModel):
    """Canonical Milestone 2.5 configuration."""

    enabled: bool = True
    strict: bool = True
    include_engineering_memory: bool = True
    include_traceability: bool = True
    include_risks: bool = True
    max_sections: int = Field(default=50, ge=1, le=500)
    max_risks: int = Field(default=250, ge=0, le=5000)
    max_traceability_items: int = Field(default=1000, ge=0, le=20000)


class MissionReportingValidationMessage(FrozenModel):
    """One validation message."""

    severity: MissionReportingValidationSeverity
    code: str
    message: str
    field: str | None = None

    @field_validator("code", "message")
    @classmethod
    def validate_required_text(
        cls,
        value: str,
    ) -> str:
        normalized = value.strip()

        if not normalized:
            raise ValueError("Value cannot be blank.")

        return normalized


class MissionReportingValidationResult(FrozenModel):
    """Mission Reporting validation result."""

    valid: bool
    messages: tuple[MissionReportingValidationMessage, ...] = ()

    @model_validator(mode="after")
    def validate_consistency(self) -> "MissionReportingValidationResult":
        has_errors = any(
            message.severity is MissionReportingValidationSeverity.ERROR
            for message in self.messages
        )

        if self.valid == has_errors:
            raise ValueError("Validation result validity conflicts with messages.")

        return self


class MissionReportingResult(FrozenModel):
    """Mission Reporting operation result."""

    report: MissionReport
    report_paths: tuple[str, ...] = ()
