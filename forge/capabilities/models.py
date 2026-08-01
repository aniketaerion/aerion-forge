"""Typed contracts for the deterministic capability registry."""

from enum import StrEnum
from pathlib import PurePosixPath, PureWindowsPath

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SCHEMA_VERSION = "1.0"
REGISTRY_ID = "aerion-forge-capability-registry"


class CapabilityCategory(StrEnum):
    FOUNDATION = "foundation"
    WORKSPACE = "workspace"
    DISCOVERY = "discovery"
    INDEXING = "indexing"
    KNOWLEDGE = "knowledge"
    CONFIGURATION = "configuration"
    DIAGNOSTICS = "diagnostics"
    PLANNING = "planning"
    EXECUTION = "execution"
    VERIFICATION = "verification"
    DOCUMENTATION = "documentation"
    VERSION_CONTROL = "version_control"
    FRONTEND_ANALYSIS = "frontend_analysis"
    BACKEND_ANALYSIS = "backend_analysis"
    DATABASE_ANALYSIS = "database_analysis"
    API_ANALYSIS = "api_analysis"
    ERP_ANALYSIS = "erp_analysis"
    MOBILE_ANALYSIS = "mobile_analysis"
    EMBEDDED_ANALYSIS = "embedded_analysis"
    INTEGRATION = "integration"
    UNKNOWN = "unknown"


class CapabilityMaturity(StrEnum):
    EXPERIMENTAL = "experimental"
    ALPHA = "alpha"
    BETA = "beta"
    STABLE = "stable"
    DEPRECATED = "deprecated"


class CapabilityLifecycle(StrEnum):
    PLANNED = "planned"
    IMPLEMENTED = "implemented"
    AVAILABLE = "available"
    PARTIALLY_AVAILABLE = "partially_available"
    DISABLED = "disabled"
    DEPRECATED = "deprecated"
    REMOVED = "removed"


class CapabilityImplementationStatus(StrEnum):
    NOT_IMPLEMENTED = "not_implemented"
    IMPLEMENTED = "implemented"
    PARTIALLY_IMPLEMENTED = "partially_implemented"


class CapabilityAccessMode(StrEnum):
    READ_ONLY = "read_only"
    FORGE_INTERNAL_WRITE = "forge_internal_write"
    TARGET_MUTATING = "target_mutating"
    EXTERNAL_SIDE_EFFECT = "external_side_effect"


class CapabilityApprovalPolicy(StrEnum):
    NONE = "none"
    OPTIONAL = "optional"
    REQUIRED_FOR_HIGH_RISK = "required_for_high_risk"
    ALWAYS_REQUIRED = "always_required"
    NOT_APPLICABLE = "not_applicable"


class CapabilityAvailabilityScope(StrEnum):
    GLOBAL = "global"
    WORKSPACE = "workspace"
    REPOSITORY = "repository"
    PROJECT_TYPE = "project_type"
    ENVIRONMENT = "environment"


class CapabilityInputType(StrEnum):
    WORKSPACE_STATE = "workspace_state"
    DISCOVERY_STATE = "discovery_state"
    INDEX_STATE = "index_state"
    KNOWLEDGE_GRAPH_STATE = "knowledge_graph_state"
    CONFIGURATION = "configuration"
    REPOSITORY_PATH = "repository_path"
    USER_REQUEST = "user_request"
    SOURCE_FILES = "source_files"
    TEST_RESULTS = "test_results"
    BUILD_RESULTS = "build_results"
    GIT_STATE = "git_state"
    UNKNOWN = "unknown"


class CapabilityOutputType(StrEnum):
    WORKSPACE_STATE = "workspace_state"
    DISCOVERY_STATE = "discovery_state"
    INDEX_STATE = "index_state"
    KNOWLEDGE_GRAPH_STATE = "knowledge_graph_state"
    CAPABILITY_REGISTRY_STATE = "capability_registry_state"
    JSON_REPORT = "json_report"
    MARKDOWN_REPORT = "markdown_report"
    CLI_OUTPUT = "cli_output"
    DIAGNOSTIC_RESULT = "diagnostic_result"
    PLAN = "plan"
    PATCH = "patch"
    TEST_RESULT = "test_result"
    BUILD_RESULT = "build_result"
    REVIEW_PACKAGE = "review_package"
    UNKNOWN = "unknown"


class CapabilityChangeType(StrEnum):
    ADDED = "added"
    MODIFIED = "modified"
    REMOVED = "removed"
    UNCHANGED = "unchanged"
    STATUS_CHANGED = "status_changed"


class CapabilityValidationSeverity(StrEnum):
    WARNING = "warning"
    ERROR = "error"


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class CapabilityInput(FrozenModel):
    input_id: str
    input_type: CapabilityInputType
    name: str
    description: str
    required: bool = True
    source: str = "forge"
    schema_version: str = SCHEMA_VERSION
    path_pattern: str | None = None
    produced_by_capability: str | None = None
    sensitive: bool = False


class CapabilityOutput(FrozenModel):
    output_id: str
    output_type: CapabilityOutputType
    name: str
    description: str
    path_pattern: str | None = None
    schema_version: str = SCHEMA_VERSION
    persistent: bool = True
    deterministic: bool = True
    sensitive: bool = False


class CapabilityCommand(FrozenModel):
    command: str
    description: str
    primary: bool = False
    read_only: bool = True
    requires_target: bool = False


class CapabilityDeprecation(FrozenModel):
    deprecated: bool
    reason: str | None = None
    replacement_capability_id: str | None = None
    removal_version: str | None = None
    migration_guidance: str | None = None


class CapabilityDefinition(FrozenModel):
    capability_id: str
    display_name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    capability_version: str
    forge_version: str
    phase: str
    milestone: str
    category: CapabilityCategory
    lifecycle: CapabilityLifecycle
    maturity: CapabilityMaturity
    implementation_status: CapabilityImplementationStatus
    supported_project_types: tuple[str, ...] = ()
    required_capabilities: tuple[str, ...] = ()
    optional_capabilities: tuple[str, ...] = ()
    required_inputs: tuple[CapabilityInput, ...] = ()
    produced_outputs: tuple[CapabilityOutput, ...] = ()
    cli_commands: tuple[CapabilityCommand, ...] = ()
    access_mode: CapabilityAccessMode
    approval_policy: CapabilityApprovalPolicy
    availability_scope: CapabilityAvailabilityScope
    configuration_keys: tuple[str, ...] = ()
    documentation_paths: tuple[str, ...] = ()
    deprecation: CapabilityDeprecation | None = None
    limitations: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    schema_version: str = SCHEMA_VERSION

    @field_validator("capability_id")
    @classmethod
    def valid_id(cls, value: str) -> str:
        import re

        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value):
            raise ValueError("capability ID must be lowercase kebab-case")
        return value

    @field_validator("capability_version", "forge_version")
    @classmethod
    def valid_version(cls, value: str) -> str:
        import re

        if not re.fullmatch(r"v?\d+\.\d+(?:\.\d+)?", value):
            raise ValueError("invalid version")
        return value

    @field_validator("milestone")
    @classmethod
    def valid_milestone(cls, value: str) -> str:
        import re

        if not re.fullmatch(r"\d+\.\d+", value):
            raise ValueError("invalid milestone")
        return value

    @field_validator("documentation_paths")
    @classmethod
    def portable_docs(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if any(
            PurePosixPath(value).is_absolute()
            or PureWindowsPath(value).is_absolute()
            or "\\" in value
            or ".." in PurePosixPath(value).parts
            for value in values
        ):
            raise ValueError("documentation paths must be normalized repository-relative paths")
        return tuple(sorted(set(values)))

    @field_validator(
        "supported_project_types",
        "required_capabilities",
        "optional_capabilities",
        "configuration_keys",
        "limitations",
        "tags",
    )
    @classmethod
    def sorted_strings(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        """Canonicalize unordered declaration collections."""
        return tuple(sorted(set(values)))

    @field_validator("required_inputs")
    @classmethod
    def sorted_inputs(cls, values: tuple[CapabilityInput, ...]) -> tuple[CapabilityInput, ...]:
        return tuple(sorted(values, key=lambda item: item.input_id))

    @field_validator("produced_outputs")
    @classmethod
    def sorted_outputs(cls, values: tuple[CapabilityOutput, ...]) -> tuple[CapabilityOutput, ...]:
        return tuple(sorted(values, key=lambda item: item.output_id))

    @field_validator("cli_commands")
    @classmethod
    def sorted_commands(
        cls, values: tuple[CapabilityCommand, ...]
    ) -> tuple[CapabilityCommand, ...]:
        return tuple(sorted(values, key=lambda item: item.command))

    @model_validator(mode="after")
    def unique_nested_ids(self) -> "CapabilityDefinition":
        for label, values in (
            ("input", [x.input_id for x in self.required_inputs]),
            ("output", [x.output_id for x in self.produced_outputs]),
            ("command", [x.command for x in self.cli_commands]),
        ):
            if len(values) != len(set(values)):
                raise ValueError(f"duplicate {label} declaration")
        return self


class CapabilityEvaluation(FrozenModel):
    capability_id: str
    implementation_status: CapabilityImplementationStatus
    lifecycle: CapabilityLifecycle
    available: bool
    missing_required_capabilities: tuple[str, ...] = ()
    unavailable_required_capabilities: tuple[str, ...] = ()
    disabled: bool = False
    validation_messages: tuple[str, ...] = ()
    project_type_support: tuple[str, ...] = ()
    configuration_status: str = "enabled"
    evaluated_registry_generation: str = "pending"


class CapabilityRegistryStatistics(FrozenModel):
    total_capabilities: int
    available_capabilities: int
    planned_capabilities: int
    implemented_capabilities: int
    partially_available_capabilities: int
    disabled_capabilities: int
    deprecated_capabilities: int
    removed_capabilities: int
    read_only_capabilities: int
    forge_internal_write_capabilities: int
    target_mutating_capabilities: int
    external_side_effect_capabilities: int
    capabilities_by_category: dict[str, int]
    capabilities_by_maturity: dict[str, int]
    capabilities_by_phase: dict[str, int]
    capabilities_by_milestone: dict[str, int]


class CapabilityRegistryGeneration(FrozenModel):
    generation_id: str
    registry_fingerprint: str
    schema_version: str = SCHEMA_VERSION
    previous_generation_id: str | None = None


class CapabilityRegistry(FrozenModel):
    registry_id: str = REGISTRY_ID
    schema_version: str = SCHEMA_VERSION
    definitions: tuple[CapabilityDefinition, ...]
    evaluations: tuple[CapabilityEvaluation, ...]
    statistics: CapabilityRegistryStatistics
    generation: CapabilityRegistryGeneration


class CapabilityChange(FrozenModel):
    capability_id: str
    change_type: CapabilityChangeType
    details: tuple[str, ...] = ()


class CapabilityRegistryChangeSet(FrozenModel):
    added: tuple[CapabilityChange, ...] = ()
    modified: tuple[CapabilityChange, ...] = ()
    removed: tuple[CapabilityChange, ...] = ()
    unchanged: tuple[CapabilityChange, ...] = ()


class CapabilityRegistryStore(BaseModel):
    schema_version: str = SCHEMA_VERSION
    registry: CapabilityRegistry | None = None
    history: list[CapabilityRegistry] = Field(default_factory=list)


class CapabilityRegistryConfiguration(FrozenModel):
    enabled: bool = True
    disabled_ids: tuple[str, ...] = ()
    include_planned: bool = True
    strict_validation: bool = True
    history_limit: int = Field(default=5, ge=0, le=100)


class RegistryValidationResult(FrozenModel):
    valid: bool
    messages: tuple[str, ...] = ()


class CapabilityRegistryResult(FrozenModel):
    registry: CapabilityRegistry
    changes: CapabilityRegistryChangeSet
