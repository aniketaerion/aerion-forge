"""Immutable contracts for M3.6 Engineering Mission Orchestration."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class MissionStatus(StrEnum):
    CREATED = "created"
    VALIDATED = "validated"
    PLANNED = "planned"
    READY = "ready"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    PAUSED = "paused"
    REPAIRING = "repairing"
    RESUMING = "resuming"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class StageStatus(StrEnum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    SUCCEEDED = "succeeded"
    SKIPPED = "skipped"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StageType(StrEnum):
    MISSION_VALIDATION = "mission_validation"
    EXECUTION_REQUEST = "execution_request"
    SAFE_CHANGE_PLAN = "safe_change_plan"
    IMPACT_ASSESSMENT = "impact_assessment"
    APPROVAL_GATE = "approval_gate"
    SAFE_EDIT_DRY_RUN = "safe_edit_dry_run"
    SAFE_EDIT_APPLY = "safe_edit_apply"
    VALIDATION = "validation"
    AUTONOMOUS_REPAIR = "autonomous_repair"
    FINAL_VALIDATION = "final_validation"
    MISSION_REPORTING = "mission_reporting"


class ApprovalDecision(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


def _relative_path(value: str) -> str:
    normalized = value.replace("\\", "/").strip()
    path = PurePosixPath(normalized)
    if not normalized or path.is_absolute() or ".." in path.parts:
        raise ValueError("path must be repository-relative without traversal")
    return path.as_posix()


class MissionApproval(FrozenModel):
    decision: ApprovalDecision = ApprovalDecision.PENDING
    approved_by: str | None = None
    reason: str | None = None
    decided_at: datetime | None = None

    @model_validator(mode="after")
    def validate_decision(self) -> MissionApproval:
        if self.decision is ApprovalDecision.PENDING:
            if self.approved_by is not None or self.decided_at is not None:
                raise ValueError("pending approval cannot contain decision evidence")
            return self
        if not self.approved_by:
            raise ValueError("approval decision requires approved_by")
        if self.decided_at is None:
            object.__setattr__(self, "decided_at", datetime.now(UTC))
        return self


class MissionRequest(FrozenModel):
    mission_id: str
    repository_root: str
    objective: str
    requested_paths: tuple[str, ...]
    constraints: tuple[str, ...] = ()
    requested_outcomes: tuple[str, ...] = ()
    source_fingerprints: dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def validate_request(self) -> MissionRequest:
        if not self.objective.strip():
            raise ValueError("mission objective is required")
        if not self.requested_paths:
            raise ValueError("mission requires at least one requested path")
        normalized = tuple(_relative_path(path) for path in self.requested_paths)
        if len(normalized) != len(set(normalized)):
            raise ValueError("duplicate requested paths are not allowed")
        fingerprints = {
            _relative_path(path): fingerprint
            for path, fingerprint in self.source_fingerprints.items()
        }
        unknown = set(fingerprints).difference(normalized)
        if unknown:
            raise ValueError("source fingerprints contain unknown paths")
        object.__setattr__(self, "requested_paths", normalized)
        object.__setattr__(self, "source_fingerprints", fingerprints)
        return self


class StageDefinition(FrozenModel):
    stage_id: str
    stage_type: StageType
    name: str
    dependencies: tuple[str, ...] = ()
    approval_required: bool = False
    optional: bool = False
    max_attempts: Annotated[int, Field(ge=1, le=10)] = 1

    @model_validator(mode="after")
    def validate_definition(self) -> StageDefinition:
        if self.stage_id in self.dependencies:
            raise ValueError("stage may not depend on itself")
        if len(self.dependencies) != len(set(self.dependencies)):
            raise ValueError("duplicate stage dependencies are not allowed")
        return self


class MissionWorkflow(FrozenModel):
    workflow_id: str
    mission_id: str
    stages: tuple[StageDefinition, ...]

    @model_validator(mode="after")
    def validate_workflow(self) -> MissionWorkflow:
        if not self.stages:
            raise ValueError("workflow requires at least one stage")
        stage_ids = [stage.stage_id for stage in self.stages]
        if len(stage_ids) != len(set(stage_ids)):
            raise ValueError("duplicate stage IDs are not allowed")
        known = set(stage_ids)
        for stage in self.stages:
            unknown = set(stage.dependencies).difference(known)
            if unknown:
                raise ValueError(
                    f"stage {stage.stage_id} depends on unknown stages: {sorted(unknown)}"
                )
        return self


class StageResult(FrozenModel):
    output_artifacts: tuple[str, ...] = ()
    messages: tuple[str, ...] = ()
    metadata: dict[str, str] = Field(default_factory=dict)


class StageRun(FrozenModel):
    stage_run_id: str
    stage_id: str
    attempt_number: Annotated[int, Field(ge=1)]
    status: StageStatus
    started_at: datetime | None = None
    completed_at: datetime | None = None
    approval: MissionApproval = MissionApproval()
    result: StageResult | None = None
    errors: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_timestamps(self) -> StageRun:
        if (
            self.started_at is not None
            and self.completed_at is not None
            and self.completed_at < self.started_at
        ):
            raise ValueError("completed_at may not precede started_at")
        return self


class MissionCheckpoint(FrozenModel):
    checkpoint_id: str
    mission_id: str
    workflow_id: str
    status: MissionStatus
    stage_runs: tuple[StageRun, ...] = ()
    current_stage_id: str | None = None
    repository_fingerprint: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class MissionExecution(FrozenModel):
    request: MissionRequest
    workflow: MissionWorkflow
    status: MissionStatus = MissionStatus.CREATED
    stage_runs: tuple[StageRun, ...] = ()
    current_stage_id: str | None = None
    checkpoint_id: str | None = None
    failure_reason: str | None = None

    @model_validator(mode="after")
    def validate_execution(self) -> MissionExecution:
        if self.workflow.mission_id != self.request.mission_id:
            raise ValueError("workflow mission ID does not match request")
        known = {stage.stage_id for stage in self.workflow.stages}
        if self.current_stage_id is not None and self.current_stage_id not in known:
            raise ValueError("current_stage_id is not in workflow")
        for run in self.stage_runs:
            if run.stage_id not in known:
                raise ValueError("stage run references unknown stage")
        return self


class MissionReport(FrozenModel):
    report_id: str
    mission_id: str
    workflow_id: str
    status: MissionStatus
    stage_runs: tuple[StageRun, ...]
    started_at: datetime
    completed_at: datetime | None = None
    messages: tuple[str, ...] = ()
    output_artifacts: tuple[str, ...] = ()