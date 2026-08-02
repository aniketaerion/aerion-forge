"""Safe Change Planning domain models."""

from collections.abc import Mapping
from enum import StrEnum
from types import MappingProxyType
from typing import Annotated, TypeAlias

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    field_validator,
    model_validator,
)

SCHEMA_VERSION = "1.0"


def _serialize_string_mapping(
    value: Mapping[str, str],
) -> dict[str, str]:
    """Serialize mappings with canonical key ordering."""

    return {key: value[key] for key in sorted(value)}


def _freeze_serializable_mapping(
    value: Mapping[str, str],
) -> Mapping[str, str]:
    """Store canonical string mappings as immutable mappings."""

    normalized = {
        key.strip(): item.strip() for key, item in value.items() if key.strip() and item.strip()
    }

    return MappingProxyType(dict(sorted(normalized.items())))


SerializableStringMapping: TypeAlias = Annotated[
    Mapping[str, str],
    AfterValidator(_freeze_serializable_mapping),
    PlainSerializer(
        _serialize_string_mapping,
        return_type=dict[str, str],
        when_used="always",
    ),
]


class FrozenModel(BaseModel):
    """Immutable validated domain model."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )


def _required_text(value: str) -> str:
    normalized = value.strip()

    if not normalized:
        raise ValueError("Value cannot be blank.")

    return normalized


def _optional_text(
    value: str | None,
) -> str | None:
    if value is None:
        return None

    normalized = value.strip()
    return normalized or None


def _string_tuple(
    values: tuple[str, ...],
) -> tuple[str, ...]:
    return tuple(sorted({value.strip() for value in values if value.strip()}))


def _string_mapping(
    value: Mapping[str, str],
) -> Mapping[str, str]:
    normalized = {
        key.strip(): item.strip() for key, item in value.items() if key.strip() and item.strip()
    }

    return MappingProxyType(dict(sorted(normalized.items())))


class ChangeTargetType(StrEnum):
    FILE = "file"
    MODULE = "module"
    PACKAGE = "package"
    SERVICE = "service"
    API = "api"
    DATABASE = "database"
    CONFIGURATION = "configuration"
    INFRASTRUCTURE = "infrastructure"
    DOCUMENTATION = "documentation"
    TEST = "test"
    UNKNOWN = "unknown"


class ChangeActionType(StrEnum):
    CREATE = "create"
    MODIFY = "modify"
    DELETE = "delete"
    RENAME = "rename"
    MIGRATE = "migrate"
    CONFIGURE = "configure"
    DOCUMENT = "document"
    VERIFY = "verify"


class DependencyType(StrEnum):
    DIRECT = "direct"
    TRANSITIVE = "transitive"
    CONTRACT = "contract"
    DATA = "data"
    CONFIGURATION = "configuration"
    TEST = "test"
    UNKNOWN = "unknown"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskFactorType(StrEnum):
    FILE_COUNT = "file_count"
    MODULE_COUNT = "module_count"
    DEPENDENCY_DEPTH = "dependency_depth"
    PUBLIC_API = "public_api"
    DATABASE_SCHEMA = "database_schema"
    DATA_MIGRATION = "data_migration"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    FINANCIAL = "financial"
    INFRASTRUCTURE = "infrastructure"
    DEPLOYMENT = "deployment"
    EXTERNAL_INTEGRATION = "external_integration"
    CONFIGURATION = "configuration"
    TEST_COVERAGE_GAP = "test_coverage_gap"
    MISSING_ROLLBACK = "missing_rollback"
    MISSING_LINEAGE = "missing_lineage"
    UNKNOWN_DEPENDENCY = "unknown_dependency"
    CONCURRENCY = "concurrency"
    SECURITY = "security"
    COMPLIANCE = "compliance"


class VerificationType(StrEnum):
    STATIC_ANALYSIS = "static_analysis"
    TYPE_CHECK = "type_check"
    UNIT_TEST = "unit_test"
    INTEGRATION_TEST = "integration_test"
    CONTRACT_TEST = "contract_test"
    BUILD = "build"
    MIGRATION_DRY_RUN = "migration_dry_run"
    SECURITY_CHECK = "security_check"
    REGRESSION_TEST = "regression_test"
    MANUAL_ACCEPTANCE = "manual_acceptance"


class PlanningPhaseType(StrEnum):
    PREPARATION = "preparation"
    IMPLEMENTATION = "implementation"
    VERIFICATION = "verification"
    RELEASE = "release"


class FindingSeverity(StrEnum):
    WARNING = "warning"
    ERROR = "error"


class ChangePlanningConfiguration(FrozenModel):
    """Safe Change Planning runtime configuration."""

    schema_version: str = SCHEMA_VERSION
    enabled: bool = True
    strict_validation: bool = True
    require_rollback_for_high_risk: bool = True
    require_verification_for_mutations: bool = True
    allow_unknown_dependencies: bool = False
    low_risk_approval_required: bool = False
    max_targets: int = Field(default=500, ge=1)
    max_actions: int = Field(default=1000, ge=1)
    max_dependency_depth: int = Field(default=20, ge=1)


class ChangeRequest(FrozenModel):
    """Normalized request for one safe change plan."""

    schema_version: str = SCHEMA_VERSION
    request_id: str
    request_fingerprint: str
    mission_id: str
    task_ids: tuple[str, ...]
    objective: str
    constraints: tuple[str, ...] = ()
    requested_outcomes: tuple[str, ...] = ()
    source_fingerprints: SerializableStringMapping = Field(default_factory=dict)

    @field_validator(
        "request_id",
        "request_fingerprint",
        "mission_id",
        "objective",
    )
    @classmethod
    def normalize_required_text(
        cls,
        value: str,
    ) -> str:
        return _required_text(value)

    @field_validator(
        "task_ids",
        "constraints",
        "requested_outcomes",
        mode="before",
    )
    @classmethod
    def normalize_sequences(
        cls,
        value: tuple[str, ...],
    ) -> tuple[str, ...]:
        return _string_tuple(tuple(value))

    @field_validator(
        "source_fingerprints",
        mode="before",
    )
    @classmethod
    def normalize_mapping(
        cls,
        value: Mapping[str, str],
    ) -> Mapping[str, str]:
        return _string_mapping(value)


class ChangeTarget(FrozenModel):
    """One file, module, service, contract, or other change target."""

    target_id: str
    target_type: ChangeTargetType
    path: str
    component: str
    reason: str
    source_ids: tuple[str, ...] = ()
    metadata: SerializableStringMapping = Field(default_factory=dict)

    @field_validator(
        "target_id",
        "path",
        "component",
        "reason",
    )
    @classmethod
    def normalize_required_text(
        cls,
        value: str,
    ) -> str:
        return _required_text(value)

    @field_validator(
        "source_ids",
        mode="before",
    )
    @classmethod
    def normalize_source_ids(
        cls,
        value: tuple[str, ...],
    ) -> tuple[str, ...]:
        return _string_tuple(tuple(value))

    @field_validator(
        "metadata",
        mode="before",
    )
    @classmethod
    def normalize_metadata(
        cls,
        value: Mapping[str, str],
    ) -> Mapping[str, str]:
        return _string_mapping(value)


class ChangeAction(FrozenModel):
    """One planned action against a declared target."""

    action_id: str
    target_id: str
    action_type: ChangeActionType
    description: str
    prerequisites: tuple[str, ...] = ()
    verification_step_ids: tuple[str, ...] = ()
    rollback_step_ids: tuple[str, ...] = ()
    destructive: bool = False
    mutating: bool = True

    @field_validator(
        "action_id",
        "target_id",
        "description",
    )
    @classmethod
    def normalize_required_text(
        cls,
        value: str,
    ) -> str:
        return _required_text(value)

    @field_validator(
        "prerequisites",
        "verification_step_ids",
        "rollback_step_ids",
        mode="before",
    )
    @classmethod
    def normalize_identifiers(
        cls,
        value: tuple[str, ...],
    ) -> tuple[str, ...]:
        return _string_tuple(tuple(value))


class DependencyImpact(FrozenModel):
    """One direct or transitive dependency impact."""

    dependency_id: str
    source_target_id: str
    affected_target_id: str
    dependency_type: DependencyType
    depth: int = Field(ge=1)
    reason: str
    known: bool = True

    @field_validator(
        "dependency_id",
        "source_target_id",
        "affected_target_id",
        "reason",
    )
    @classmethod
    def normalize_required_text(
        cls,
        value: str,
    ) -> str:
        return _required_text(value)


class RiskFactor(FrozenModel):
    """One evidence-grounded contributor to planning risk."""

    factor_id: str
    factor_type: RiskFactorType
    score: int = Field(ge=0, le=100)
    reason: str
    source_ids: tuple[str, ...] = ()
    mitigation: str | None = None

    @field_validator(
        "factor_id",
        "reason",
    )
    @classmethod
    def normalize_required_text(
        cls,
        value: str,
    ) -> str:
        return _required_text(value)

    @field_validator(
        "mitigation",
        mode="before",
    )
    @classmethod
    def normalize_mitigation(
        cls,
        value: str | None,
    ) -> str | None:
        return _optional_text(value)

    @field_validator(
        "source_ids",
        mode="before",
    )
    @classmethod
    def normalize_source_ids(
        cls,
        value: tuple[str, ...],
    ) -> tuple[str, ...]:
        return _string_tuple(tuple(value))


class ChangeRiskAssessment(FrozenModel):
    """Aggregate deterministic risk assessment."""

    assessment_id: str
    risk_level: RiskLevel
    score: int = Field(ge=0, le=100)
    factors: tuple[RiskFactor, ...] = ()
    approval_required: bool
    mitigations: tuple[str, ...] = ()

    @field_validator("assessment_id")
    @classmethod
    def normalize_assessment_id(
        cls,
        value: str,
    ) -> str:
        return _required_text(value)

    @field_validator(
        "mitigations",
        mode="before",
    )
    @classmethod
    def normalize_mitigations(
        cls,
        value: tuple[str, ...],
    ) -> tuple[str, ...]:
        return _string_tuple(tuple(value))

    @model_validator(mode="after")
    def validate_risk_controls(
        self,
    ) -> "ChangeRiskAssessment":
        elevated = self.risk_level in {
            RiskLevel.HIGH,
            RiskLevel.CRITICAL,
        }

        if elevated and not self.approval_required:
            raise ValueError("High and critical risks require approval.")

        if elevated and not self.mitigations:
            raise ValueError("High and critical risks require mitigations.")

        return self


class VerificationStep(FrozenModel):
    """One planned verification activity."""

    step_id: str
    verification_type: VerificationType
    description: str
    target_ids: tuple[str, ...]
    command: str | None = None
    required: bool = True

    @field_validator(
        "step_id",
        "description",
    )
    @classmethod
    def normalize_required_text(
        cls,
        value: str,
    ) -> str:
        return _required_text(value)

    @field_validator(
        "command",
        mode="before",
    )
    @classmethod
    def normalize_command(
        cls,
        value: str | None,
    ) -> str | None:
        return _optional_text(value)

    @field_validator(
        "target_ids",
        mode="before",
    )
    @classmethod
    def normalize_target_ids(
        cls,
        value: tuple[str, ...],
    ) -> tuple[str, ...]:
        return _string_tuple(tuple(value))


class RollbackStep(FrozenModel):
    """One planned rollback or compensation activity."""

    step_id: str
    description: str
    target_ids: tuple[str, ...]
    irreversible: bool = False
    limitation: str | None = None

    @field_validator(
        "step_id",
        "description",
    )
    @classmethod
    def normalize_required_text(
        cls,
        value: str,
    ) -> str:
        return _required_text(value)

    @field_validator(
        "limitation",
        mode="before",
    )
    @classmethod
    def normalize_limitation(
        cls,
        value: str | None,
    ) -> str | None:
        return _optional_text(value)

    @field_validator(
        "target_ids",
        mode="before",
    )
    @classmethod
    def normalize_target_ids(
        cls,
        value: tuple[str, ...],
    ) -> tuple[str, ...]:
        return _string_tuple(tuple(value))

    @model_validator(mode="after")
    def validate_irreversible_step(
        self,
    ) -> "RollbackStep":
        if self.irreversible and not self.limitation:
            raise ValueError("Irreversible rollback steps require a limitation.")

        return self


class ChangePhase(FrozenModel):
    """One ordered phase in the safe change plan."""

    phase_id: str
    phase_type: PlanningPhaseType
    sequence: int = Field(ge=1)
    title: str
    action_ids: tuple[str, ...]

    @field_validator(
        "phase_id",
        "title",
    )
    @classmethod
    def normalize_required_text(
        cls,
        value: str,
    ) -> str:
        return _required_text(value)

    @field_validator(
        "action_ids",
        mode="before",
    )
    @classmethod
    def normalize_action_ids(
        cls,
        value: tuple[str, ...],
    ) -> tuple[str, ...]:
        return _string_tuple(tuple(value))


class PlanStatistics(FrozenModel):
    """Calculated Safe Change Plan statistics."""

    target_count: int = Field(ge=0)
    action_count: int = Field(ge=0)
    dependency_count: int = Field(ge=0)
    verification_count: int = Field(ge=0)
    rollback_count: int = Field(ge=0)
    phase_count: int = Field(ge=0)
    high_risk_factor_count: int = Field(ge=0)


class SafeChangePlan(FrozenModel):
    """Top-level immutable Safe Change Plan."""

    schema_version: str = SCHEMA_VERSION
    plan_id: str
    plan_fingerprint: str
    request: ChangeRequest
    targets: tuple[ChangeTarget, ...]
    actions: tuple[ChangeAction, ...]
    dependencies: tuple[DependencyImpact, ...] = ()
    risk_assessment: ChangeRiskAssessment
    verification_steps: tuple[VerificationStep, ...]
    rollback_steps: tuple[RollbackStep, ...] = ()
    phases: tuple[ChangePhase, ...]
    statistics: PlanStatistics
    source_fingerprints: SerializableStringMapping = Field(default_factory=dict)

    @field_validator(
        "plan_id",
        "plan_fingerprint",
    )
    @classmethod
    def normalize_identity(
        cls,
        value: str,
    ) -> str:
        return _required_text(value)

    @field_validator(
        "source_fingerprints",
        mode="before",
    )
    @classmethod
    def normalize_source_fingerprints(
        cls,
        value: Mapping[str, str],
    ) -> Mapping[str, str]:
        return _string_mapping(value)

    @model_validator(mode="after")
    def validate_plan_consistency(
        self,
    ) -> "SafeChangePlan":
        target_ids = {target.target_id for target in self.targets}
        action_ids = {action.action_id for action in self.actions}
        verification_ids = {step.step_id for step in self.verification_steps}
        rollback_ids = {step.step_id for step in self.rollback_steps}

        if len(target_ids) != len(self.targets):
            raise ValueError("Duplicate change target identifiers.")

        if len(action_ids) != len(self.actions):
            raise ValueError("Duplicate change action identifiers.")

        for action in self.actions:
            if action.target_id not in target_ids:
                raise ValueError("Action references an unknown target.")

            if not set(action.verification_step_ids).issubset(verification_ids):
                raise ValueError("Action references unknown verification steps.")

            if not set(action.rollback_step_ids).issubset(rollback_ids):
                raise ValueError("Action references unknown rollback steps.")

        for phase in self.phases:
            if not set(phase.action_ids).issubset(action_ids):
                raise ValueError("Phase references unknown actions.")

        expected = PlanStatistics(
            target_count=len(self.targets),
            action_count=len(self.actions),
            dependency_count=len(self.dependencies),
            verification_count=len(self.verification_steps),
            rollback_count=len(self.rollback_steps),
            phase_count=len(self.phases),
            high_risk_factor_count=sum(
                factor.score >= 70 for factor in self.risk_assessment.factors
            ),
        )

        if self.statistics != expected:
            raise ValueError("Plan statistics do not match plan contents.")

        return self


class PlanningValidationFinding(FrozenModel):
    """One deterministic planning validation finding."""

    code: str
    message: str
    severity: FindingSeverity
    source_ids: tuple[str, ...] = ()

    @field_validator(
        "code",
        "message",
    )
    @classmethod
    def normalize_required_text(
        cls,
        value: str,
    ) -> str:
        return _required_text(value)

    @field_validator(
        "source_ids",
        mode="before",
    )
    @classmethod
    def normalize_source_ids(
        cls,
        value: tuple[str, ...],
    ) -> tuple[str, ...]:
        return _string_tuple(tuple(value))

    @property
    def is_error(self) -> bool:
        return self.severity is FindingSeverity.ERROR


class PlanningValidationResult(FrozenModel):
    """Deterministic planning validation result."""

    valid: bool
    findings: tuple[PlanningValidationFinding, ...] = ()

    @model_validator(mode="after")
    def validate_result(
        self,
    ) -> "PlanningValidationResult":
        contains_error = any(finding.is_error for finding in self.findings)

        if self.valid and contains_error:
            raise ValueError("Valid result cannot contain error findings.")

        if not self.valid and not contains_error:
            raise ValueError("Invalid result must contain an error finding.")

        return self
