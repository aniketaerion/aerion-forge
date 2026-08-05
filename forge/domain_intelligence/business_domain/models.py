"""Immutable contracts for M4.5 Business Domain Intelligence."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BusinessDomainKind(StrEnum):
    ERP = "erp"
    CRM = "crm"
    GENERIC = "generic"
    UNKNOWN = "unknown"


class BusinessEntityKind(StrEnum):
    MASTER_DATA = "master_data"
    TRANSACTION = "transaction"
    DOCUMENT = "document"
    PARTY = "party"
    PRODUCT = "product"
    LOCATION = "location"
    FINANCIAL = "financial"
    WORKFLOW = "workflow"
    UNKNOWN = "unknown"


class BusinessRuleSeverity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class BusinessFindingSeverity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ImmutableBusinessDomainModel(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        str_strip_whitespace=True,
    )


class BusinessDomainAnalysisRequest(
    ImmutableBusinessDomainModel
):
    repository_root: str = Field(min_length=1)
    project_root: str = Field(default=".", min_length=1)
    max_files: int = Field(default=10000, ge=1, le=100000)


class BusinessEntity(ImmutableBusinessDomainModel):
    entity_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    kind: BusinessEntityKind
    module: str | None = None
    source_paths: tuple[str, ...] = ()
    attributes: tuple[str, ...] = ()


class BusinessWorkflowStep(ImmutableBusinessDomainModel):
    name: str = Field(min_length=1)
    sequence: int = Field(ge=1)
    entity_names: tuple[str, ...] = ()


class BusinessWorkflow(ImmutableBusinessDomainModel):
    workflow_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    module: str | None = None
    steps: tuple[BusinessWorkflowStep, ...] = ()

    @field_validator("steps")
    @classmethod
    def ensure_unique_step_sequence(
        cls,
        steps: tuple[BusinessWorkflowStep, ...],
    ) -> tuple[BusinessWorkflowStep, ...]:
        sequences = [step.sequence for step in steps]
        if len(sequences) != len(set(sequences)):
            raise ValueError("workflow step sequence must be unique")
        return steps


class BusinessRule(ImmutableBusinessDomainModel):
    rule_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    severity: BusinessRuleSeverity
    module: str | None = None
    entity_names: tuple[str, ...] = ()
    source_path: str | None = None


class BusinessDomainProject(ImmutableBusinessDomainModel):
    project_id: str = Field(min_length=1)
    root: str = Field(min_length=1)
    domains: tuple[BusinessDomainKind, ...] = ()
    modules: tuple[str, ...] = ()
    source_files: tuple[str, ...] = ()
    configuration_files: tuple[str, ...] = ()
    detected_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )


class BusinessDomainFinding(ImmutableBusinessDomainModel):
    finding_id: str = Field(min_length=1)
    category: str = Field(min_length=1)
    severity: BusinessFindingSeverity
    message: str = Field(min_length=1)
    path: str | None = None
    evidence: dict[str, str] = Field(default_factory=dict)


class BusinessDomainAnalysisReport(
    ImmutableBusinessDomainModel
):
    report_id: str = Field(min_length=1)
    project: BusinessDomainProject
    entities: tuple[BusinessEntity, ...] = ()
    workflows: tuple[BusinessWorkflow, ...] = ()
    rules: tuple[BusinessRule, ...] = ()
    findings: tuple[BusinessDomainFinding, ...] = ()
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )

    @field_validator("findings")
    @classmethod
    def ensure_unique_findings(
        cls,
        findings: tuple[BusinessDomainFinding, ...],
    ) -> tuple[BusinessDomainFinding, ...]:
        identifiers = [finding.finding_id for finding in findings]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError(
                "business-domain finding identifiers must be unique"
            )
        return findings