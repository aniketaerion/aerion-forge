"""Typed mission-planning domain model (schema 1.0)."""

from collections.abc import Mapping
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = "1.0"


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class MissionPlanningStatus(StrEnum):
    DRAFT = "draft"
    READY = "ready"
    READY_WITH_CONDITIONS = "ready_with_conditions"
    BLOCKED = "blocked"
    INVALID = "invalid"
    SUPERSEDED = "superseded"


class MissionRequestCategory(StrEnum):
    COMPLETE = "complete"
    IMPLEMENT = "implement"
    FIX = "fix"
    IMPROVE = "improve"
    UPGRADE = "upgrade"
    REFACTOR = "refactor"
    INTEGRATE = "integrate"
    DOCUMENT = "document"
    ANALYZE = "analyze"
    INVESTIGATE = "investigate"
    MIGRATE = "migrate"
    VALIDATE = "validate"
    REMOVE = "remove"
    UNKNOWN = "unknown"


class MissionRiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class MissionApprovalLevel(StrEnum):
    REVIEW_REQUIRED = "review_required"
    ARCHITECTURE_APPROVAL = "architecture_approval"
    SECURITY_APPROVAL = "security_approval"
    DOMAIN_OWNER_APPROVAL = "domain_owner_approval"
    DATA_MIGRATION_APPROVAL = "data_migration_approval"
    HIGH_RISK_APPROVAL = "high_risk_approval"
    RELEASE_APPROVAL = "release_approval"


class PlanningConfidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INSUFFICIENT = "insufficient"


class MissionScopeType(StrEnum):
    IN_SCOPE = "in_scope"
    OUT_OF_SCOPE = "out_of_scope"
    CONDITIONAL = "conditional"
    UNKNOWN = "unknown"


class MissionPrerequisiteStatus(StrEnum):
    SATISFIED = "satisfied"
    UNSATISFIED = "unsatisfied"
    UNKNOWN = "unknown"


class MissionAffectedAreaType(StrEnum):
    WORKSPACE = "workspace"
    APPLICATION = "application"
    SERVICE = "service"
    LIBRARY = "library"
    MODULE = "module"
    DIRECTORY = "directory"
    MANIFEST = "manifest"
    DATABASE_AREA = "database_area"
    MIGRATION_AREA = "migration_area"
    CONFIGURATION_AREA = "configuration_area"
    TEST_AREA = "test_area"
    DOCUMENTATION_AREA = "documentation_area"
    INFRASTRUCTURE_AREA = "infrastructure_area"
    UNKNOWN = "unknown"


class MissionValidationCategory(StrEnum):
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
    RELEASE_VALIDATION = "release_validation"
    UNKNOWN = "unknown"


class MissionChangeType(StrEnum):
    CREATED = "created"
    UNCHANGED = "unchanged"
    UPDATED = "updated"


class MissionValidationSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class EngineeringRequest(FrozenModel):
    raw_request: str
    target: str | None = None


class NormalizedEngineeringRequest(FrozenModel):
    raw_request: str
    normalized_request: str
    primary_action: str
    primary_object: str
    category: MissionRequestCategory
    target_domain_phrase: str | None = None
    ambiguity: PlanningConfidence
    terms: tuple[str, ...] = ()


class MissionObjective(FrozenModel):
    statement: str


class MissionScopeItem(FrozenModel):
    scope_id: str
    scope_type: MissionScopeType
    statement: str


class MissionAssumption(FrozenModel):
    assumption_id: str
    statement: str
    basis: str
    risk_if_incorrect: str
    requires_confirmation: bool


class MissionConstraint(FrozenModel):
    constraint_id: str
    statement: str


class MissionPrerequisite(FrozenModel):
    prerequisite_id: str
    description: str
    status: MissionPrerequisiteStatus
    blocking: bool
    evidence: str
    corrective_action: str | None = None


class MissionContextReference(FrozenModel):
    entity_id: str
    entity_type: str
    canonical_name: str
    relationship_to_request: str
    evidence: str
    confidence: PlanningConfidence


class MissionAffectedArea(FrozenModel):
    area_id: str
    area_type: MissionAffectedAreaType
    canonical_name: str
    evidence: str
    confidence: PlanningConfidence


class MissionWorkstream(FrozenModel):
    workstream_id: str
    name: str
    objective: str
    expected_outputs: tuple[str, ...]
    dependencies: tuple[str, ...] = ()
    risk_level: MissionRiskLevel = MissionRiskLevel.MEDIUM
    required_approvals: tuple[MissionApprovalLevel, ...] = ()
    completion_criteria: tuple[str, ...] = ()


class MissionDeliverable(FrozenModel):
    deliverable_id: str
    description: str


class MissionAcceptanceCriterion(FrozenModel):
    criterion_id: str
    statement: str


class MissionValidationStrategy(FrozenModel):
    strategy_id: str
    category: MissionValidationCategory
    description: str


class MissionRisk(FrozenModel):
    risk_id: str
    level: MissionRiskLevel
    statement: str
    evidence: str
    mitigation: str


class MissionApprovalRequirement(FrozenModel):
    approval_id: str
    level: MissionApprovalLevel
    reason: str


class MissionQuestion(FrozenModel):
    question_id: str
    question: str
    blocking: bool = False


class MissionPlanStatistics(FrozenModel):
    affected_area_count: int = Field(ge=0)
    workstream_count: int = Field(ge=0)
    assumption_count: int = Field(ge=0)
    question_count: int = Field(ge=0)
    blocking_prerequisite_count: int = Field(ge=0)


class MissionPlan(FrozenModel):
    schema_version: str = SCHEMA_VERSION
    mission_id: str
    mission_fingerprint: str
    request: NormalizedEngineeringRequest
    target_identity: str
    target_name: str
    workspace_identity: str
    source_fingerprints: Mapping[str, str]
    objective: MissionObjective
    status: MissionPlanningStatus
    planning_confidence: PlanningConfidence
    risk_level: MissionRiskLevel
    scope: tuple[MissionScopeItem, ...]
    assumptions: tuple[MissionAssumption, ...]
    constraints: tuple[MissionConstraint, ...]
    prerequisites: tuple[MissionPrerequisite, ...]
    context: tuple[MissionContextReference, ...]
    affected_areas: tuple[MissionAffectedArea, ...]
    workstreams: tuple[MissionWorkstream, ...]
    deliverables: tuple[MissionDeliverable, ...]
    acceptance_criteria: tuple[MissionAcceptanceCriterion, ...]
    validation_strategy: tuple[MissionValidationStrategy, ...]
    risks: tuple[MissionRisk, ...]
    approvals: tuple[MissionApprovalRequirement, ...]
    questions: tuple[MissionQuestion, ...]
    statistics: MissionPlanStatistics


class MissionPlanGeneration(FrozenModel):
    schema_version: str = SCHEMA_VERSION
    generation_id: str
    previous_generation_id: str | None = None
    mission_id: str
    mission_fingerprint: str
    target_identity: str
    workspace_identity: str
    discovery_identity: str
    index_fingerprint: str
    graph_fingerprint: str
    configuration_fingerprint: str
    capability_fingerprint: str
    diagnostic_fingerprint: str
    mission_status: MissionPlanningStatus
    planning_confidence: PlanningConfidence
    risk_level: MissionRiskLevel
    affected_area_count: int
    workstream_count: int
    assumption_count: int
    question_count: int
    blocking_prerequisite_count: int


class MissionPlanChange(FrozenModel):
    field: str
    change_type: MissionChangeType


class MissionPlanChangeSet(FrozenModel):
    mission_id: str
    changes: tuple[MissionPlanChange, ...] = ()


class MissionPlanStore(BaseModel):
    schema_version: str = SCHEMA_VERSION
    missions: dict[str, MissionPlan] = Field(default_factory=dict)
    history: dict[str, list[MissionPlan]] = Field(default_factory=dict)


class MissionPlanResult(FrozenModel):
    plan: MissionPlan
    generation: MissionPlanGeneration
    changes: MissionPlanChangeSet
    report_paths: tuple[str, ...] = ()


class MissionPlanningConfiguration(FrozenModel):
    enabled: bool = True
    strict: bool = False
    history_limit: int = Field(default=5, ge=0, le=100)
    max_affected_areas: int = Field(default=25, ge=1, le=1000)
    max_workstreams: int = Field(default=8, ge=1, le=50)
    max_assumptions: int = Field(default=12, ge=1, le=100)
    max_questions: int = Field(default=12, ge=1, le=100)
    require_current_graph: bool = True
    allow_degraded_runtime: bool = True


class MissionValidationMessage(FrozenModel):
    severity: MissionValidationSeverity
    field: str
    message: str


class MissionValidationResult(FrozenModel):
    valid: bool
    messages: tuple[MissionValidationMessage, ...] = ()


