"""Immutable contracts for M3.8 Unified Agent Runtime."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from pathlib import PurePosixPath

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class AgentCapability(StrEnum):
    """Forge capabilities orchestrated by the unified runtime."""

    REPOSITORY_DISCOVERY = "repository_discovery"
    PROJECT_INDEX = "project_index"
    KNOWLEDGE_GRAPH = "knowledge_graph"
    MISSION_PLANNING = "mission_planning"
    TASK_MANAGEMENT = "task_management"
    IMPACT_ANALYSIS = "impact_analysis"
    SAFE_CHANGE_PLANNING = "safe_change_planning"
    SAFE_CODE_EDITING = "safe_code_editing"
    VALIDATION_REPAIR = "validation_repair"
    AUTONOMOUS_REPAIR = "autonomous_repair"
    MISSION_ORCHESTRATION = "mission_orchestration"
    BUILD_VERIFICATION = "build_verification"


class AgentSessionStatus(StrEnum):
    """Lifecycle state for one agent session."""

    CREATED = "created"
    PLANNING = "planning"
    AWAITING_APPROVAL = "awaiting_approval"
    EXECUTING = "executing"
    VALIDATING = "validating"
    REPAIRING = "repairing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class AgentStageStatus(StrEnum):
    """Lifecycle state for one agent stage."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


class ApprovalKind(StrEnum):
    """Human approval boundaries enforced by the runtime."""

    PLAN = "plan"
    EDIT = "edit"
    REPAIR = "repair"
    RELEASE = "release"


class AgentEventType(StrEnum):
    """Audit event emitted by the unified runtime."""

    SESSION_CREATED = "session_created"
    STAGE_STARTED = "stage_started"
    STAGE_COMPLETED = "stage_completed"
    STAGE_FAILED = "stage_failed"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_GRANTED = "approval_granted"
    APPROVAL_REJECTED = "approval_rejected"
    CHECKPOINT_WRITTEN = "checkpoint_written"
    SESSION_COMPLETED = "session_completed"
    SESSION_FAILED = "session_failed"
    SESSION_CANCELLED = "session_cancelled"


class ImmutableModel(BaseModel):
    """Shared immutable model configuration."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        str_strip_whitespace=True,
    )


class AgentObjective(ImmutableModel):
    """User-provided engineering objective."""

    objective: str = Field(min_length=3)
    repository_root: str = Field(min_length=1)
    target_paths: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    acceptance_criteria: tuple[str, ...] = ()
    requested_capabilities: tuple[AgentCapability, ...] = ()
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )

    @field_validator("target_paths")
    @classmethod
    def validate_target_paths(
        cls,
        values: tuple[str, ...],
    ) -> tuple[str, ...]:
        normalized: list[str] = []

        for value in values:
            path = PurePosixPath(value.replace("\\", "/"))

            if path.is_absolute() or ".." in path.parts:
                raise ValueError(
                    "target paths must remain repository-relative"
                )

            normalized.append(path.as_posix())

        return tuple(sorted(set(normalized)))


class AgentApproval(ImmutableModel):
    """Explicit human approval for one controlled operation."""

    approval_id: str = Field(min_length=1)
    kind: ApprovalKind
    approved: bool
    approved_by: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    approved_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )


class AgentStage(ImmutableModel):
    """One capability-backed stage in a unified agent session."""

    stage_id: str = Field(min_length=1)
    sequence: int = Field(ge=1)
    capability: AgentCapability
    name: str = Field(min_length=1)
    required: bool = True
    requires_approval: ApprovalKind | None = None
    depends_on: tuple[str, ...] = ()


class AgentStageResult(ImmutableModel):
    """Captured result for one runtime stage."""

    stage_id: str = Field(min_length=1)
    status: AgentStageStatus
    summary: str = Field(min_length=1)
    artifact_paths: tuple[str, ...] = ()
    evidence: dict[str, str] = Field(default_factory=dict)
    started_at: datetime | None = None
    completed_at: datetime | None = None

    @model_validator(mode="after")
    def validate_terminal_result(self) -> AgentStageResult:
        terminal = {
            AgentStageStatus.SUCCEEDED,
            AgentStageStatus.FAILED,
            AgentStageStatus.BLOCKED,
            AgentStageStatus.SKIPPED,
        }

        if self.status in terminal and self.completed_at is None:
            raise ValueError(
                "terminal stage results require completed_at"
            )

        return self


class AgentRuntimeRequest(ImmutableModel):
    """Bounded request to start one unified agent session."""

    request_id: str = Field(min_length=1)
    objective: AgentObjective
    dry_run: bool = True
    allow_code_changes: bool = False
    max_stages: int = Field(default=20, ge=1, le=100)
    max_repair_attempts: int = Field(default=3, ge=0, le=10)


class AgentSession(ImmutableModel):
    """Persistent state for one unified engineering agent session."""

    session_id: str = Field(min_length=1)
    request: AgentRuntimeRequest
    status: AgentSessionStatus
    stages: tuple[AgentStage, ...] = Field(min_length=1)
    stage_results: tuple[AgentStageResult, ...] = ()
    approvals: tuple[AgentApproval, ...] = ()
    current_stage_id: str | None = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )

    @model_validator(mode="after")
    def validate_stage_graph(self) -> AgentSession:
        stage_ids = [stage.stage_id for stage in self.stages]

        if len(stage_ids) != len(set(stage_ids)):
            raise ValueError("agent stage identifiers must be unique")

        known = set(stage_ids)
        for stage in self.stages:
            unknown = set(stage.depends_on) - known
            if unknown:
                raise ValueError(
                    "agent stage dependency references unknown stages"
                )

        return self


class AgentCheckpoint(ImmutableModel):
    """Recoverable snapshot of one agent session."""

    checkpoint_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    status: AgentSessionStatus
    current_stage_id: str | None = None
    completed_stage_ids: tuple[str, ...] = ()
    repository_revision: str = Field(min_length=1)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )


class AgentEvent(ImmutableModel):
    """Structured telemetry event for runtime observability."""

    event_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    event_type: AgentEventType
    message: str = Field(min_length=1)
    stage_id: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)
    occurred_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )


class AgentRuntimePolicy(ImmutableModel):
    """Safety and execution policy for the unified runtime."""

    allowed_capabilities: tuple[AgentCapability, ...] = tuple(
        AgentCapability
    )
    max_stages: int = Field(default=20, ge=1, le=100)
    max_repair_attempts: int = Field(default=3, ge=0, le=10)
    require_plan_approval: bool = True
    require_edit_approval: bool = True
    require_repair_approval: bool = True
    require_release_approval: bool = True
    allow_code_changes: bool = False
    allow_network: bool = False
    allow_self_modification: bool = False
    require_clean_working_tree: bool = True