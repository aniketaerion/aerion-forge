"""Typed contracts for the Milestone 2.3 Impact Decision Engine."""

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


class ImpactCategory(StrEnum):
    """Controlled impact classifications."""

    ARCHITECTURE = "architecture"
    API_CONTRACT = "api_contract"
    DATA = "data"
    DATABASE = "database"
    SECURITY = "security"
    CONFIGURATION = "configuration"
    INTEGRATION = "integration"
    INFRASTRUCTURE = "infrastructure"
    PERFORMANCE = "performance"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    OPERATIONS = "operations"
    COMPLIANCE = "compliance"
    UNKNOWN = "unknown"


class ImpactScope(StrEnum):
    """Controlled affected scopes."""

    TASK = "task"
    WORKSTREAM = "workstream"
    MISSION = "mission"
    APPLICATION = "application"
    SERVICE = "service"
    LIBRARY = "library"
    MODULE = "module"
    DATABASE = "database"
    CONFIGURATION = "configuration"
    INFRASTRUCTURE = "infrastructure"
    RELEASE = "release"
    UNKNOWN = "unknown"


class ImpactSeverity(StrEnum):
    """Controlled impact severity."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class DecisionType(StrEnum):
    """Controlled engineering decision types."""

    PROCEED = "proceed"
    PROCEED_WITH_CONDITIONS = "proceed_with_conditions"
    REVISE = "revise"
    DEFER = "defer"
    REJECT = "reject"
    ESCALATE = "escalate"
    INVESTIGATE = "investigate"


class DecisionStatus(StrEnum):
    """Controlled decision lifecycle."""

    DRAFT = "draft"
    READY = "ready"
    READY_WITH_CONDITIONS = "ready_with_conditions"
    BLOCKED = "blocked"
    APPROVAL_REQUIRED = "approval_required"
    SUPERSEDED = "superseded"


class DecisionConfidence(StrEnum):
    """Controlled recommendation confidence."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INSUFFICIENT = "insufficient"


class ImpactApprovalLevel(StrEnum):
    """Controlled approval requirements."""

    REVIEW_REQUIRED = "review_required"
    ARCHITECTURE_APPROVAL = "architecture_approval"
    SECURITY_APPROVAL = "security_approval"
    DOMAIN_OWNER_APPROVAL = "domain_owner_approval"
    DATA_MIGRATION_APPROVAL = "data_migration_approval"
    HIGH_RISK_APPROVAL = "high_risk_approval"
    RELEASE_APPROVAL = "release_approval"


class ImpactValidationCategory(StrEnum):
    """Controlled validation obligations."""

    STATIC_ANALYSIS = "static_analysis"
    TYPE_CHECKING = "type_checking"
    UNIT_TESTING = "unit_testing"
    INTEGRATION_TESTING = "integration_testing"
    CONTRACT_TESTING = "contract_testing"
    DATABASE_TESTING = "database_testing"
    MIGRATION_VALIDATION = "migration_validation"
    BUILD_VALIDATION = "build_validation"
    SECURITY_VALIDATION = "security_validation"
    PERFORMANCE_VALIDATION = "performance_validation"
    DOCUMENTATION_VALIDATION = "documentation_validation"
    MANUAL_REVIEW = "manual_review"


class ImpactValidationSeverity(StrEnum):
    """Validation-message severity."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ImpactFinding(FrozenModel):
    """One deterministic impact finding."""

    finding_id: str
    category: ImpactCategory
    scope: ImpactScope
    severity: ImpactSeverity
    summary: str
    rationale: str
    affected_task_ids: tuple[str, ...] = ()
    affected_components: tuple[str, ...] = ()
    evidence_references: tuple[str, ...] = ()

    @field_validator(
        "finding_id",
        "summary",
        "rationale",
    )
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Impact finding fields cannot be blank.")
        return normalized

    @field_validator(
        "affected_task_ids",
        "affected_components",
        "evidence_references",
    )
    @classmethod
    def normalize_values(
        cls,
        value: tuple[str, ...],
    ) -> tuple[str, ...]:
        return tuple(sorted({item.strip() for item in value if item.strip()}))

    @model_validator(mode="after")
    def require_affected_target(self) -> "ImpactFinding":
        if (
            not self.affected_task_ids
            and not self.affected_components
            and self.scope is ImpactScope.UNKNOWN
        ):
            raise ValueError(
                "An impact finding must identify an affected task, component, or controlled scope."
            )
        return self


class DecisionOption(FrozenModel):
    """One candidate decision option."""

    option_id: str
    title: str
    description: str
    decision_type: DecisionType
    benefits: tuple[str, ...] = ()
    tradeoffs: tuple[str, ...] = ()
    residual_risks: tuple[str, ...] = ()

    @field_validator(
        "option_id",
        "title",
        "description",
    )
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Decision option fields cannot be blank.")
        return normalized


class DecisionApprovalRequirement(FrozenModel):
    """One required human approval."""

    requirement_id: str
    level: ImpactApprovalLevel
    reason: str

    @field_validator("requirement_id", "reason")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Approval requirement fields cannot be blank.")
        return normalized


class DecisionValidationRequirement(FrozenModel):
    """One post-decision validation obligation."""

    requirement_id: str
    category: ImpactValidationCategory
    description: str
    blocking: bool = True

    @field_validator("requirement_id", "description")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Validation requirement fields cannot be blank.")
        return normalized


class DecisionRecommendation(FrozenModel):
    """Deterministic recommendation over candidate options."""

    recommendation_id: str
    selected_option_id: str
    options: tuple[DecisionOption, ...]
    rationale: str
    confidence: DecisionConfidence
    approval_requirements: tuple[
        DecisionApprovalRequirement,
        ...,
    ] = ()
    validation_requirements: tuple[
        DecisionValidationRequirement,
        ...,
    ]
    conditions: tuple[str, ...] = ()

    @field_validator(
        "recommendation_id",
        "selected_option_id",
        "rationale",
    )
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Decision recommendation fields cannot be blank.")
        return normalized

    @model_validator(mode="after")
    def validate_recommendation(
        self,
    ) -> "DecisionRecommendation":
        if not self.options:
            raise ValueError("A recommendation requires at least one decision option.")

        option_ids = [option.option_id for option in self.options]

        if len(option_ids) != len(set(option_ids)):
            raise ValueError("Decision option IDs must be unique.")

        if self.selected_option_id not in option_ids:
            raise ValueError("The selected option must exist in the option set.")

        if not self.validation_requirements:
            raise ValueError("A recommendation requires validation obligations.")

        return self


class ImpactStatistics(FrozenModel):
    """Summary statistics for an assessment."""

    finding_count: int = Field(ge=0)
    affected_task_count: int = Field(ge=0)
    affected_component_count: int = Field(ge=0)
    high_impact_count: int = Field(ge=0)
    critical_impact_count: int = Field(ge=0)


class ImpactAssessment(FrozenModel):
    """Canonical impact assessment and recommendation."""

    schema_version: str = SCHEMA_VERSION
    assessment_id: str
    assessment_fingerprint: str
    mission_id: str
    task_set_fingerprint: str
    task_ids: tuple[str, ...]
    findings: tuple[ImpactFinding, ...]
    recommendation: DecisionRecommendation
    status: DecisionStatus
    confidence: DecisionConfidence
    overall_severity: ImpactSeverity
    statistics: ImpactStatistics
    blocking_reason: str | None = None
    source_fingerprints: Mapping[str, str] = Field(default_factory=dict)

    @field_validator(
        "assessment_id",
        "assessment_fingerprint",
        "mission_id",
        "task_set_fingerprint",
    )
    @classmethod
    def reject_blank_identity(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Impact assessment identity fields cannot be blank.")
        return normalized

    @field_validator("task_ids")
    @classmethod
    def normalize_task_ids(
        cls,
        value: tuple[str, ...],
    ) -> tuple[str, ...]:
        return tuple(sorted({task_id.strip() for task_id in value if task_id.strip()}))

    @model_validator(mode="after")
    def validate_assessment(self) -> "ImpactAssessment":
        if not self.findings:
            raise ValueError("An impact assessment requires at least one finding.")

        if self.status is DecisionStatus.BLOCKED:
            if not self.blocking_reason:
                raise ValueError("A blocked decision requires a blocking reason.")
        elif self.blocking_reason is not None:
            raise ValueError("Only blocked decisions may declare a blocking reason.")

        severe = self.overall_severity in {
            ImpactSeverity.HIGH,
            ImpactSeverity.CRITICAL,
        }

        if severe and not self.recommendation.approval_requirements:
            raise ValueError("High or critical impact requires approval.")

        return self


class ImpactDecisionGeneration(FrozenModel):
    """Deterministic generation metadata."""

    schema_version: str = SCHEMA_VERSION
    generation_id: str
    previous_generation_id: str | None = None
    assessment_id: str
    assessment_fingerprint: str
    mission_id: str
    task_set_fingerprint: str
    finding_count: int = Field(ge=0)

    @field_validator(
        "generation_id",
        "assessment_id",
        "assessment_fingerprint",
        "mission_id",
        "task_set_fingerprint",
    )
    @classmethod
    def reject_blank_identity(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Generation identity fields cannot be blank.")
        return normalized


class ImpactDecisionStore(BaseModel):
    """Persisted Impact Decision state."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    assessments: dict[str, ImpactAssessment] = Field(default_factory=dict)
    history: dict[str, list[ImpactAssessment]] = Field(default_factory=dict)
    generations: dict[str, ImpactDecisionGeneration] = Field(default_factory=dict)


class ImpactDecisionConfiguration(FrozenModel):
    """Canonical Milestone 2.3 configuration."""

    enabled: bool = True
    strict: bool = False
    history_limit: int = Field(default=5, ge=0, le=100)
    max_findings: int = Field(default=250, ge=1, le=5000)
    max_options: int = Field(default=12, ge=1, le=100)
    max_affected_tasks: int = Field(
        default=500,
        ge=1,
        le=10000,
    )
    max_affected_components: int = Field(
        default=500,
        ge=1,
        le=10000,
    )
    require_validation_requirements: bool = True
    require_approval_for_high_impact: bool = True


class ImpactValidationMessage(FrozenModel):
    """One model or aggregate validation message."""

    severity: ImpactValidationSeverity
    field: str
    message: str
    assessment_id: str | None = None


class ImpactValidationResult(FrozenModel):
    """Impact validation result."""

    valid: bool
    messages: tuple[ImpactValidationMessage, ...] = ()


class ImpactDecisionResult(FrozenModel):
    """Impact Decision operation result."""

    assessment: ImpactAssessment
    generation: ImpactDecisionGeneration
    report_paths: tuple[str, ...] = ()
