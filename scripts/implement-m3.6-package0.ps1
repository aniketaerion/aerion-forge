[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

function Write-Utf8NoBom {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$Content
    )

    $FullPath = Join-Path $RepositoryRoot $Path
    $Directory = Split-Path $FullPath -Parent
    New-Item -ItemType Directory -Path $Directory -Force | Out-Null

    [System.IO.File]::WriteAllText(
        $FullPath,
        $Content,
        [System.Text.UTF8Encoding]::new($false)
    )

    Write-Host "WROTE $Path" -ForegroundColor Green
}

Write-Utf8NoBom "forge\mission_orchestration\errors.py" @'
"""Typed errors for M3.6 Engineering Mission Orchestration."""


class MissionOrchestrationError(RuntimeError):
    """Base error for mission orchestration."""


class MissionValidationError(MissionOrchestrationError):
    """Raised when a mission request or state is invalid."""


class MissionPolicyViolationError(MissionOrchestrationError):
    """Raised when orchestration violates policy."""


class MissionStateTransitionError(MissionOrchestrationError):
    """Raised when a mission state transition is invalid."""


class MissionStageNotFoundError(MissionOrchestrationError):
    """Raised when a workflow stage cannot be resolved."""


class MissionStageConflictError(MissionOrchestrationError):
    """Raised when duplicate stage registration conflicts."""


class MissionDependencyError(MissionOrchestrationError):
    """Raised when stage dependencies are invalid or incomplete."""


class MissionCheckpointError(MissionOrchestrationError):
    """Raised when checkpoint persistence fails."""


class MissionRecoveryError(MissionOrchestrationError):
    """Raised when a paused or failed mission cannot recover."""


class MissionCancellationError(MissionOrchestrationError):
    """Raised when cancellation cannot be completed safely."""


class MissionExecutionError(MissionOrchestrationError):
    """Raised when stage or mission execution fails."""


class MissionReportError(MissionOrchestrationError):
    """Raised when orchestration evidence cannot be rendered or persisted."""
'@

Write-Utf8NoBom "forge\mission_orchestration\identifiers.py" @'
"""Deterministic identifiers for M3.6 Mission Orchestration."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any


def sha256_text(value: str) -> str:
    """Return a SHA-256 digest for UTF-8 text."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def stable_identifier(
    prefix: str,
    payload: Mapping[str, Any] | Sequence[Any] | str,
) -> str:
    """Return a stable identifier from canonical JSON."""
    if isinstance(payload, str):
        canonical = payload
    else:
        canonical = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            default=str,
        )
    return f"{prefix}_{sha256_text(canonical)[:24]}"


def mission_identifier(payload: Mapping[str, Any]) -> str:
    return stable_identifier("mission", payload)


def workflow_identifier(payload: Mapping[str, Any]) -> str:
    return stable_identifier("workflow", payload)


def stage_run_identifier(payload: Mapping[str, Any]) -> str:
    return stable_identifier("stagerun", payload)


def checkpoint_identifier(payload: Mapping[str, Any]) -> str:
    return stable_identifier("checkpoint", payload)


def orchestration_report_identifier(payload: Mapping[str, Any]) -> str:
    return stable_identifier("missionreport", payload)
'@

Write-Utf8NoBom "forge\mission_orchestration\models.py" @'
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
'@

Write-Utf8NoBom "forge\mission_orchestration\policies.py" @'
"""Safety policy for M3.6 Mission Orchestration."""

from __future__ import annotations

from pathlib import Path, PurePosixPath

from pydantic import Field

from forge.mission_orchestration.errors import MissionPolicyViolationError
from forge.mission_orchestration.models import FrozenModel, StageType


class MissionOrchestrationPolicy(FrozenModel):
    max_stage_attempts: int = Field(default=3, ge=1, le=10)
    max_total_stage_runs: int = Field(default=50, ge=1, le=500)
    max_requested_paths: int = Field(default=25, ge=1, le=500)
    require_approval_for_apply: bool = True
    require_approval_for_high_risk: bool = True
    require_repository_fingerprint: bool = True
    checkpoint_after_each_stage: bool = True
    stop_on_repository_state_change: bool = True
    allow_resume: bool = True
    allow_cancellation: bool = True
    allow_git_mutation: bool = False
    allow_dependency_installation: bool = False
    allow_arbitrary_shell: bool = False
    protected_paths: tuple[str, ...] = (
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "reports",
        "audit",
        "memory",
    )
    required_stages: tuple[StageType, ...] = (
        StageType.MISSION_VALIDATION,
        StageType.EXECUTION_REQUEST,
        StageType.SAFE_CHANGE_PLAN,
        StageType.IMPACT_ASSESSMENT,
        StageType.APPROVAL_GATE,
        StageType.SAFE_EDIT_DRY_RUN,
        StageType.SAFE_EDIT_APPLY,
        StageType.VALIDATION,
        StageType.FINAL_VALIDATION,
        StageType.MISSION_REPORTING,
    )

    def validate_paths(self, paths: tuple[str, ...]) -> tuple[str, ...]:
        if len(paths) > self.max_requested_paths:
            raise MissionPolicyViolationError(
                "mission exceeds maximum requested paths"
            )
        normalized: list[str] = []
        for raw_path in paths:
            path = PurePosixPath(raw_path.replace("\\", "/").strip())
            if path.is_absolute() or ".." in path.parts or not path.parts:
                raise MissionPolicyViolationError(
                    f"invalid mission path: {raw_path}"
                )
            if path.parts[0] in self.protected_paths:
                raise MissionPolicyViolationError(
                    f"protected mission path: {raw_path}"
                )
            normalized.append(path.as_posix())
        return tuple(normalized)

    def validate_stage_attempts(self, attempts: int) -> None:
        if attempts > self.max_stage_attempts:
            raise MissionPolicyViolationError(
                "stage attempt count exceeds policy limit"
            )

    @staticmethod
    def resolve_repository(repository_root: Path) -> Path:
        root = repository_root.expanduser().resolve()
        if not root.is_dir():
            raise MissionPolicyViolationError(
                f"repository root does not exist: {root}"
            )
        return root
'@

Write-Utf8NoBom "forge\mission_orchestration\__init__.py" @'
"""M3.6 Engineering Mission Orchestration contracts."""

from forge.mission_orchestration.identifiers import (
    checkpoint_identifier,
    mission_identifier,
    orchestration_report_identifier,
    sha256_text,
    stable_identifier,
    stage_run_identifier,
    workflow_identifier,
)
from forge.mission_orchestration.models import (
    ApprovalDecision,
    MissionApproval,
    MissionCheckpoint,
    MissionExecution,
    MissionReport,
    MissionRequest,
    MissionStatus,
    MissionWorkflow,
    StageDefinition,
    StageResult,
    StageRun,
    StageStatus,
    StageType,
)
from forge.mission_orchestration.policies import MissionOrchestrationPolicy

__all__ = [
    "ApprovalDecision",
    "MissionApproval",
    "MissionCheckpoint",
    "MissionExecution",
    "MissionOrchestrationPolicy",
    "MissionReport",
    "MissionRequest",
    "MissionStatus",
    "MissionWorkflow",
    "StageDefinition",
    "StageResult",
    "StageRun",
    "StageStatus",
    "StageType",
    "checkpoint_identifier",
    "mission_identifier",
    "orchestration_report_identifier",
    "sha256_text",
    "stable_identifier",
    "stage_run_identifier",
    "workflow_identifier",
]
'@

Write-Utf8NoBom "tests\test_mission_orchestration_identifiers.py" @'
from forge.mission_orchestration.identifiers import (
    checkpoint_identifier,
    mission_identifier,
    stable_identifier,
)


def test_stable_identifier_is_order_independent() -> None:
    assert stable_identifier("x", {"a": 1, "b": 2}) == stable_identifier(
        "x", {"b": 2, "a": 1}
    )


def test_mission_identifier_has_expected_prefix() -> None:
    assert mission_identifier({"objective": "test"}).startswith("mission_")


def test_checkpoint_identifier_changes_with_payload() -> None:
    assert checkpoint_identifier({"x": 1}) != checkpoint_identifier({"x": 2})
'@

Write-Utf8NoBom "tests\test_mission_orchestration_models.py" @'
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from forge.mission_orchestration.models import (
    ApprovalDecision,
    MissionApproval,
    MissionExecution,
    MissionRequest,
    MissionStatus,
    MissionWorkflow,
    StageDefinition,
    StageRun,
    StageStatus,
    StageType,
)


def request() -> MissionRequest:
    return MissionRequest(
        mission_id="mission-1",
        repository_root=".",
        objective="Implement bounded change",
        requested_paths=("forge/app.py",),
    )


def workflow() -> MissionWorkflow:
    validate = StageDefinition(
        stage_id="validate",
        stage_type=StageType.MISSION_VALIDATION,
        name="Validate mission",
    )
    plan = StageDefinition(
        stage_id="plan",
        stage_type=StageType.SAFE_CHANGE_PLAN,
        name="Plan safe change",
        dependencies=("validate",),
    )
    return MissionWorkflow(
        workflow_id="workflow-1",
        mission_id="mission-1",
        stages=(validate, plan),
    )


def test_request_rejects_path_traversal() -> None:
    with pytest.raises(ValidationError):
        MissionRequest(
            mission_id="mission-1",
            repository_root=".",
            objective="unsafe",
            requested_paths=("../secret.py",),
        )


def test_workflow_rejects_unknown_dependency() -> None:
    with pytest.raises(ValidationError):
        MissionWorkflow(
            workflow_id="workflow-1",
            mission_id="mission-1",
            stages=(
                StageDefinition(
                    stage_id="plan",
                    stage_type=StageType.SAFE_CHANGE_PLAN,
                    name="Plan",
                    dependencies=("missing",),
                ),
            ),
        )


def test_execution_rejects_mismatched_mission() -> None:
    with pytest.raises(ValidationError):
        MissionExecution(
            request=request(),
            workflow=MissionWorkflow(
                workflow_id="workflow-2",
                mission_id="different",
                stages=workflow().stages,
            ),
        )


def test_approval_requires_approver_identity() -> None:
    with pytest.raises(ValidationError):
        MissionApproval(decision=ApprovalDecision.APPROVED)


def test_models_are_immutable() -> None:
    item = StageRun(
        stage_run_id="run-1",
        stage_id="validate",
        attempt_number=1,
        status=StageStatus.RUNNING,
        started_at=datetime.now(UTC),
    )
    with pytest.raises(ValidationError):
        item.status = StageStatus.SUCCEEDED


def test_execution_accepts_known_current_stage() -> None:
    execution = MissionExecution(
        request=request(),
        workflow=workflow(),
        status=MissionStatus.RUNNING,
        current_stage_id="validate",
    )
    assert execution.current_stage_id == "validate"
'@

Write-Utf8NoBom "tests\test_mission_orchestration_policies.py" @'
from pathlib import Path

import pytest

from forge.mission_orchestration.errors import MissionPolicyViolationError
from forge.mission_orchestration.policies import MissionOrchestrationPolicy


def test_policy_defaults_are_bounded() -> None:
    policy = MissionOrchestrationPolicy()
    assert policy.max_stage_attempts == 3
    assert policy.checkpoint_after_each_stage is True
    assert policy.allow_git_mutation is False
    assert policy.allow_arbitrary_shell is False


def test_policy_rejects_protected_path() -> None:
    with pytest.raises(MissionPolicyViolationError):
        MissionOrchestrationPolicy().validate_paths((".git/config",))


def test_policy_rejects_excess_stage_attempts() -> None:
    with pytest.raises(MissionPolicyViolationError):
        MissionOrchestrationPolicy().validate_stage_attempts(4)


def test_policy_resolves_existing_repository(tmp_path: Path) -> None:
    assert MissionOrchestrationPolicy.resolve_repository(tmp_path) == tmp_path.resolve()
'@

Write-Utf8NoBom "docs\mission_orchestration\ARCHITECTURE.md" @'
# M3.6 Engineering Mission Orchestration Architecture

## Objective

Connect the released M3.1–M3.5 capabilities into one deterministic, resumable and auditable engineering mission workflow.

## Pipeline

1. Mission validation.
2. Execution request.
3. Safe Change Planning.
4. Impact assessment.
5. Approval gate.
6. Safe-edit dry-run.
7. Safe-edit apply.
8. Validation.
9. Autonomous repair when required.
10. Final validation.
11. Mission reporting.

## Safety boundary

M3.6 v1 does not permit autonomous Git commits, Git merges, dependency installation, arbitrary shell execution, silent approval or unbounded retry loops.
'@

Write-Utf8NoBom "docs\mission_orchestration\SPECIFICATION.md" @'
# M3.6 Engineering Mission Orchestration Specification

M3.6 coordinates existing Forge subsystems rather than duplicating them.

A mission contains an immutable request, deterministic workflow, stage runs, checkpoints, approval evidence and a final report.

Execution must remain bounded by repository fingerprints, stage dependencies, maximum attempts, protected paths, approval requirements and checkpoint persistence.
'@

Write-Utf8NoBom "docs\mission_orchestration\DATA_MODEL.md" @'
# M3.6 Data Model

Core immutable contracts:

- `MissionRequest`
- `MissionWorkflow`
- `StageDefinition`
- `StageRun`
- `StageResult`
- `MissionApproval`
- `MissionCheckpoint`
- `MissionExecution`
- `MissionReport`

All mission, workflow, stage-run, checkpoint and report identifiers are deterministic.
'@

Write-Utf8NoBom "docs\mission_orchestration\STATE_MACHINE.md" @'
# M3.6 State Machine

Primary path:

`CREATED → VALIDATED → PLANNED → READY → RUNNING → COMPLETED`

Approval path:

`RUNNING → AWAITING_APPROVAL → RUNNING`

Recovery path:

`RUNNING → PAUSED → RESUMING → RUNNING`

Repair path:

`RUNNING → REPAIRING → RUNNING`

Terminal states:

- `COMPLETED`
- `CANCELLED`
- `FAILED`
'@

Write-Utf8NoBom "docs\mission_orchestration\FAILURE_AND_RECOVERY.md" @'
# M3.6 Failure and Recovery

Recoverable failures pause the mission and persist a checkpoint.

Resume is allowed only when the repository fingerprint still matches, the workflow is unchanged, required stages remain registered, attempt limits are not exhausted, and approval policy has not weakened.
'@

Write-Utf8NoBom "docs\mission_orchestration\SECURITY_MODEL.md" @'
# M3.6 Security Model

Controls include repository-relative paths, protected-path rejection, repository fingerprint verification, explicit approval gates, bounded attempts and stage runs, dependency validation, checkpoints, no arbitrary shell, no Git mutation and no dependency installation.
'@

Write-Utf8NoBom "docs\mission_orchestration\ACCEPTANCE_CRITERIA.md" @'
# M3.6 Acceptance Criteria

M3.6 is complete when workflow ordering is deterministic, invalid dependencies are rejected, stages are registered deterministically, missions checkpoint after each stage, execution can pause and resume safely, approval gates block mutation, M3.1–M3.5 are invoked through adapters, validation failure can route to autonomous repair, repository drift blocks resume, and CLI and validators pass.
'@

Write-Host ""
Write-Host "M3.6 Package 0 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m mypy .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m pytest `
    .\tests\test_mission_orchestration_identifiers.py `
    .\tests\test_mission_orchestration_models.py `
    .\tests\test_mission_orchestration_policies.py `
    -p no:cacheprovider
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m pytest -p no:cacheprovider
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "M3.6 PACKAGE 0 COMPLETE" -ForegroundColor Green
git status --short
