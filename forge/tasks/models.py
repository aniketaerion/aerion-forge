"""Typed Task Management domain models for schema 1.0."""

from collections.abc import Mapping
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SCHEMA_VERSION = "1.0"


class FrozenModel(BaseModel):
    """Immutable strict base model."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        validate_default=True,
    )


class TaskStatus(StrEnum):
    """Controlled engineering-task lifecycle states."""

    DRAFT = "draft"
    READY = "ready"
    BLOCKED = "blocked"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    VALIDATED = "validated"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    SUPERSEDED = "superseded"


class TaskPriority(StrEnum):
    """Controlled task priority."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskRiskLevel(StrEnum):
    """Controlled task risk."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class TaskDependencyType(StrEnum):
    """Task relationship type."""

    REQUIRES = "requires"
    BLOCKS = "blocks"
    RELATES_TO = "relates_to"
    PARENT_OF = "parent_of"
    CHILD_OF = "child_of"


class TaskOwnershipType(StrEnum):
    """Task ownership classification."""

    UNASSIGNED = "unassigned"
    ROLE = "role"
    PERSON = "person"
    TEAM = "team"
    SYSTEM_PLACEHOLDER = "system_placeholder"


class TaskValidationCategory(StrEnum):
    """Controlled task-level validation categories."""

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


class TaskApprovalLevel(StrEnum):
    """Approval inherited or required by a task."""

    REVIEW_REQUIRED = "review_required"
    ARCHITECTURE_APPROVAL = "architecture_approval"
    SECURITY_APPROVAL = "security_approval"
    DOMAIN_OWNER_APPROVAL = "domain_owner_approval"
    DATA_MIGRATION_APPROVAL = "data_migration_approval"
    HIGH_RISK_APPROVAL = "high_risk_approval"
    RELEASE_APPROVAL = "release_approval"


class TaskChangeType(StrEnum):
    """Task change classification."""

    CREATED = "created"
    UNCHANGED = "unchanged"
    UPDATED = "updated"
    STATUS_CHANGED = "status_changed"
    OWNER_CHANGED = "owner_changed"
    DEPENDENCY_CHANGED = "dependency_changed"
    SUPERSEDED = "superseded"


class TaskValidationSeverity(StrEnum):
    """Validation message severity."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class TaskOwner(FrozenModel):
    """Task ownership placeholder."""

    ownership_type: TaskOwnershipType = TaskOwnershipType.UNASSIGNED
    owner_id: str | None = None
    display_name: str | None = None

    @model_validator(mode="after")
    def validate_owner(self) -> "TaskOwner":
        if self.ownership_type is TaskOwnershipType.UNASSIGNED:
            if self.owner_id is not None or self.display_name is not None:
                raise ValueError(
                    "Unassigned ownership cannot declare owner details."
                )
        elif not self.owner_id or not self.display_name:
            raise ValueError(
                "Assigned ownership requires owner_id and display_name."
            )

        return self


class TaskDependency(FrozenModel):
    """Typed dependency between engineering tasks."""

    task_id: str
    dependency_task_id: str
    dependency_type: TaskDependencyType
    blocking: bool = True
    reason: str

    @model_validator(mode="after")
    def reject_self_dependency(self) -> "TaskDependency":
        if self.task_id == self.dependency_task_id:
            raise ValueError("A task cannot depend on itself.")

        return self


class TaskAcceptanceCriterion(FrozenModel):
    """Task-level completion requirement."""

    criterion_id: str
    statement: str
    mandatory: bool = True
    inherited_from_mission: bool = False


class TaskValidationRequirement(FrozenModel):
    """Task-level validation requirement."""

    requirement_id: str
    category: TaskValidationCategory
    description: str
    mandatory: bool = True
    inherited_from_mission: bool = False


class TaskApprovalRequirement(FrozenModel):
    """Task-level approval requirement."""

    approval_id: str
    level: TaskApprovalLevel
    reason: str
    inherited_from_mission: bool = False


class TaskSourceReference(FrozenModel):
    """Stable source reference from the originating mission."""

    reference_id: str
    reference_type: str
    canonical_name: str
    evidence: str


class EngineeringTask(FrozenModel):
    """Canonical engineering task."""

    schema_version: str = SCHEMA_VERSION
    task_id: str
    task_fingerprint: str
    mission_id: str
    workstream_id: str
    parent_task_id: str | None = None
    title: str
    description: str
    status: TaskStatus = TaskStatus.DRAFT
    priority: TaskPriority = TaskPriority.MEDIUM
    risk_level: TaskRiskLevel = TaskRiskLevel.MEDIUM
    owner: TaskOwner = Field(default_factory=TaskOwner)
    dependencies: tuple[TaskDependency, ...] = ()
    acceptance_criteria: tuple[TaskAcceptanceCriterion, ...]
    validation_requirements: tuple[TaskValidationRequirement, ...]
    approval_requirements: tuple[TaskApprovalRequirement, ...] = ()
    source_references: tuple[TaskSourceReference, ...] = ()
    tags: tuple[str, ...] = ()
    sequence: int = Field(ge=0)
    blocking_reason: str | None = None

    @field_validator("title", "description")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        normalized = value.strip()

        if not normalized:
            raise ValueError("Task title and description cannot be blank.")

        return normalized

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    tag.strip().casefold()
                    for tag in value
                    if tag.strip()
                }
            )
        )

    @model_validator(mode="after")
    def validate_state(self) -> "EngineeringTask":
        if not self.acceptance_criteria:
            raise ValueError(
                "Engineering tasks require acceptance criteria."
            )

        if not self.validation_requirements:
            raise ValueError(
                "Engineering tasks require validation requirements."
            )

        if self.status is TaskStatus.BLOCKED and not self.blocking_reason:
            raise ValueError(
                "Blocked tasks require a blocking reason."
            )

        if (
            self.status is not TaskStatus.BLOCKED
            and self.blocking_reason is not None
        ):
            raise ValueError(
                "Only blocked tasks may declare a blocking reason."
            )

        dependency_ids = [
            item.dependency_task_id
            for item in self.dependencies
        ]

        if len(dependency_ids) != len(set(dependency_ids)):
            raise ValueError(
                "Duplicate dependency targets are not allowed."
            )

        return self


class TaskStatistics(FrozenModel):
    """Aggregated task statistics."""

    total_tasks: int = Field(ge=0)
    draft_tasks: int = Field(ge=0)
    ready_tasks: int = Field(ge=0)
    blocked_tasks: int = Field(ge=0)
    in_progress_tasks: int = Field(ge=0)
    review_tasks: int = Field(ge=0)
    validated_tasks: int = Field(ge=0)
    completed_tasks: int = Field(ge=0)
    cancelled_tasks: int = Field(ge=0)
    superseded_tasks: int = Field(ge=0)
    unresolved_dependency_count: int = Field(ge=0)


class TaskGeneration(FrozenModel):
    """Deterministic task-set generation metadata."""

    schema_version: str = SCHEMA_VERSION
    generation_id: str
    previous_generation_id: str | None = None
    mission_id: str
    mission_fingerprint: str
    task_set_fingerprint: str
    task_count: int = Field(ge=0)
    statistics: TaskStatistics


class TaskChange(FrozenModel):
    """One deterministic task change."""

    task_id: str
    field: str
    change_type: TaskChangeType


class TaskChangeSet(FrozenModel):
    """Changes for one task generation."""

    mission_id: str
    changes: tuple[TaskChange, ...] = ()


class TaskStore(BaseModel):
    """Persisted task store."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    tasks: dict[str, EngineeringTask] = Field(default_factory=dict)
    history: dict[str, list[EngineeringTask]] = Field(default_factory=dict)
    generations: dict[str, TaskGeneration] = Field(default_factory=dict)


class TaskResult(FrozenModel):
    """Task-management operation result."""

    tasks: tuple[EngineeringTask, ...]
    generation: TaskGeneration
    changes: TaskChangeSet
    report_paths: tuple[str, ...] = ()


class TaskManagementConfiguration(FrozenModel):
    """Canonical Milestone 2.2 configuration."""

    enabled: bool = True
    strict: bool = False
    history_limit: int = Field(default=5, ge=0, le=100)
    max_tasks_per_mission: int = Field(default=250, ge=1, le=5000)
    max_dependencies_per_task: int = Field(default=25, ge=0, le=250)
    max_acceptance_criteria_per_task: int = Field(
        default=25,
        ge=1,
        le=250,
    )
    max_validation_requirements_per_task: int = Field(
        default=25,
        ge=1,
        le=250,
    )
    require_approved_mission: bool = True
    allow_blocked_tasks: bool = True


class TaskValidationMessage(FrozenModel):
    """One task-validation message."""

    severity: TaskValidationSeverity
    field: str
    message: str
    task_id: str | None = None


class TaskValidationResult(FrozenModel):
    """Task validation result."""

    valid: bool
    messages: tuple[TaskValidationMessage, ...] = ()


class TaskSet(FrozenModel):
    """Canonical task collection for one mission."""

    schema_version: str = SCHEMA_VERSION
    mission_id: str
    mission_fingerprint: str
    task_set_fingerprint: str
    tasks: tuple[EngineeringTask, ...]
    statistics: TaskStatistics
    source_fingerprints: Mapping[str, str] = Field(default_factory=dict)
