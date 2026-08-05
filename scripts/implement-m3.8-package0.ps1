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

function Assert-CommandSuccess {
    param([Parameter(Mandatory)][string]$Name)

    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

Write-Utf8NoBom "forge\agent_runtime\errors.py" @'
"""Typed errors for M3.8 Unified Agent Runtime."""

from __future__ import annotations


class AgentRuntimeError(Exception):
    """Base error for the unified agent runtime."""


class AgentRuntimeConfigurationError(AgentRuntimeError):
    """Raised when runtime configuration is invalid."""


class AgentRuntimePolicyError(AgentRuntimeError):
    """Raised when an agent request violates policy."""


class AgentRuntimeValidationError(AgentRuntimeError):
    """Raised when runtime state or evidence is invalid."""


class AgentRuntimeCapabilityError(AgentRuntimeError):
    """Raised when a required Forge capability is unavailable."""


class AgentRuntimeStateError(AgentRuntimeError):
    """Raised when an invalid lifecycle transition is requested."""


class AgentRuntimeApprovalError(AgentRuntimeError):
    """Raised when required human approval is missing or invalid."""


class AgentRuntimePersistenceError(AgentRuntimeError):
    """Raised when agent state cannot be persisted."""


class AgentRuntimeRecoveryError(AgentRuntimeError):
    """Raised when a session cannot be recovered safely."""


class AgentRuntimeExecutionError(AgentRuntimeError):
    """Raised when a runtime stage cannot execute safely."""


class AgentRuntimeReportError(AgentRuntimeError):
    """Raised when runtime evidence cannot be reported."""
'@

Write-Utf8NoBom "forge\agent_runtime\identifiers.py" @'
"""Stable identifiers for M3.8 Unified Agent Runtime."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any


def _normalize(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _normalize(item)
            for key, item in sorted(
                value.items(),
                key=lambda pair: str(pair[0]),
            )
        }

    if isinstance(value, Sequence) and not isinstance(
        value,
        str | bytes | bytearray,
    ):
        return [_normalize(item) for item in value]

    if hasattr(value, "model_dump"):
        return _normalize(value.model_dump(mode="json"))

    if hasattr(value, "value"):
        return _normalize(value.value)

    return value


def stable_identifier(prefix: str, payload: Any) -> str:
    """Build a deterministic identifier from normalized JSON."""
    encoded = json.dumps(
        _normalize(payload),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")

    digest = hashlib.sha256(encoded).hexdigest()[:24]
    return f"{prefix}-{digest}"


def agent_request_identifier(payload: Any) -> str:
    """Build a deterministic agent request identifier."""
    return stable_identifier("agent-request", payload)


def agent_session_identifier(payload: Any) -> str:
    """Build a deterministic agent session identifier."""
    return stable_identifier("agent-session", payload)


def agent_stage_identifier(payload: Any) -> str:
    """Build a deterministic agent stage identifier."""
    return stable_identifier("agent-stage", payload)


def agent_event_identifier(payload: Any) -> str:
    """Build a deterministic agent event identifier."""
    return stable_identifier("agent-event", payload)


def agent_checkpoint_identifier(payload: Any) -> str:
    """Build a deterministic agent checkpoint identifier."""
    return stable_identifier("agent-checkpoint", payload)
'@

Write-Utf8NoBom "forge\agent_runtime\models.py" @'
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
'@

Write-Utf8NoBom "forge\agent_runtime\policies.py" @'
"""Policy enforcement for M3.8 Unified Agent Runtime."""

from __future__ import annotations

from pathlib import Path

from forge.agent_runtime.errors import (
    AgentRuntimeApprovalError,
    AgentRuntimePolicyError,
)
from forge.agent_runtime.models import (
    AgentApproval,
    AgentRuntimePolicy,
    AgentRuntimeRequest,
    ApprovalKind,
)


def resolve_repository_root(
    repository_root: str | Path,
) -> Path:
    """Resolve and validate a Git repository root."""
    root = Path(repository_root).expanduser().resolve()

    if not root.is_dir():
        raise AgentRuntimePolicyError(
            f"repository root does not exist: {root}"
        )

    if not (root / ".git").exists():
        raise AgentRuntimePolicyError(
            f"repository root is not a Git repository: {root}"
        )

    return root


def validate_request(
    request: AgentRuntimeRequest,
    policy: AgentRuntimePolicy,
) -> None:
    """Validate a runtime request against safety policy."""
    if request.max_stages > policy.max_stages:
        raise AgentRuntimePolicyError(
            f"request exceeds maximum stage count: {policy.max_stages}"
        )

    if request.max_repair_attempts > policy.max_repair_attempts:
        raise AgentRuntimePolicyError(
            "request exceeds maximum repair attempts"
        )

    requested = set(request.objective.requested_capabilities)
    allowed = set(policy.allowed_capabilities)
    disallowed = requested - allowed

    if disallowed:
        names = ", ".join(sorted(item.value for item in disallowed))
        raise AgentRuntimePolicyError(
            f"requested capabilities are not allowed: {names}"
        )

    if request.allow_code_changes and not policy.allow_code_changes:
        raise AgentRuntimePolicyError(
            "code changes are disabled by runtime policy"
        )


def approval_required(
    kind: ApprovalKind,
    policy: AgentRuntimePolicy,
) -> bool:
    """Return whether policy requires the given approval kind."""
    mapping = {
        ApprovalKind.PLAN: policy.require_plan_approval,
        ApprovalKind.EDIT: policy.require_edit_approval,
        ApprovalKind.REPAIR: policy.require_repair_approval,
        ApprovalKind.RELEASE: policy.require_release_approval,
    }
    return mapping[kind]


def require_approval(
    approvals: tuple[AgentApproval, ...],
    kind: ApprovalKind,
    policy: AgentRuntimePolicy,
) -> AgentApproval | None:
    """Return a valid approval or fail closed."""
    if not approval_required(kind, policy):
        return None

    matching = [
        approval
        for approval in approvals
        if approval.kind is kind and approval.approved
    ]

    if not matching:
        raise AgentRuntimeApprovalError(
            f"missing required approval: {kind.value}"
        )

    return max(matching, key=lambda item: item.approved_at)


def validate_self_modification(
    repository_root: Path,
    target_paths: tuple[str, ...],
    policy: AgentRuntimePolicy,
) -> None:
    """Reject runtime self-modification unless explicitly enabled."""
    if policy.allow_self_modification:
        return

    runtime_root = (repository_root / "forge" / "agent_runtime").resolve()

    for relative_path in target_paths:
        candidate = (repository_root / relative_path).resolve()

        try:
            candidate.relative_to(runtime_root)
        except ValueError:
            continue

        raise AgentRuntimePolicyError(
            "self-modification of agent_runtime is disabled"
        )
'@

Write-Utf8NoBom "forge\agent_runtime\__init__.py" @'
"""M3.8 Unified Agent Runtime public API."""

from forge.agent_runtime.errors import (
    AgentRuntimeApprovalError,
    AgentRuntimeCapabilityError,
    AgentRuntimeConfigurationError,
    AgentRuntimeError,
    AgentRuntimeExecutionError,
    AgentRuntimePersistenceError,
    AgentRuntimePolicyError,
    AgentRuntimeRecoveryError,
    AgentRuntimeReportError,
    AgentRuntimeStateError,
    AgentRuntimeValidationError,
)
from forge.agent_runtime.identifiers import (
    agent_checkpoint_identifier,
    agent_event_identifier,
    agent_request_identifier,
    agent_session_identifier,
    agent_stage_identifier,
    stable_identifier,
)
from forge.agent_runtime.models import (
    AgentApproval,
    AgentCapability,
    AgentCheckpoint,
    AgentEvent,
    AgentEventType,
    AgentObjective,
    AgentRuntimePolicy,
    AgentRuntimeRequest,
    AgentSession,
    AgentSessionStatus,
    AgentStage,
    AgentStageResult,
    AgentStageStatus,
    ApprovalKind,
)
from forge.agent_runtime.policies import (
    approval_required,
    require_approval,
    resolve_repository_root,
    validate_request,
    validate_self_modification,
)

__all__ = [
    "AgentApproval",
    "AgentCapability",
    "AgentCheckpoint",
    "AgentEvent",
    "AgentEventType",
    "AgentObjective",
    "AgentRuntimeApprovalError",
    "AgentRuntimeCapabilityError",
    "AgentRuntimeConfigurationError",
    "AgentRuntimeError",
    "AgentRuntimeExecutionError",
    "AgentRuntimePersistenceError",
    "AgentRuntimePolicy",
    "AgentRuntimePolicyError",
    "AgentRuntimeRecoveryError",
    "AgentRuntimeReportError",
    "AgentRuntimeRequest",
    "AgentRuntimeStateError",
    "AgentRuntimeValidationError",
    "AgentSession",
    "AgentSessionStatus",
    "AgentStage",
    "AgentStageResult",
    "AgentStageStatus",
    "ApprovalKind",
    "agent_checkpoint_identifier",
    "agent_event_identifier",
    "agent_request_identifier",
    "agent_session_identifier",
    "agent_stage_identifier",
    "approval_required",
    "require_approval",
    "resolve_repository_root",
    "stable_identifier",
    "validate_request",
    "validate_self_modification",
]
'@

Write-Utf8NoBom "tests\test_agent_runtime_identifiers.py" @'
from forge.agent_runtime.identifiers import (
    agent_request_identifier,
    agent_session_identifier,
    stable_identifier,
)


def test_stable_identifier_is_deterministic() -> None:
    first = stable_identifier(
        "sample",
        {"objective": "build", "paths": ["b.py", "a.py"]},
    )
    second = stable_identifier(
        "sample",
        {"paths": ["b.py", "a.py"], "objective": "build"},
    )

    assert first == second
    assert first.startswith("sample-")


def test_request_identifier_changes_with_objective() -> None:
    first = agent_request_identifier({"objective": "one"})
    second = agent_request_identifier({"objective": "two"})

    assert first != second


def test_session_identifier_has_expected_prefix() -> None:
    identifier = agent_session_identifier(
        {"request_id": "request-1", "revision": "abc"}
    )

    assert identifier.startswith("agent-session-")
'@

Write-Utf8NoBom "tests\test_agent_runtime_models.py" @'
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from forge.agent_runtime.models import (
    AgentCapability,
    AgentObjective,
    AgentRuntimeRequest,
    AgentSession,
    AgentSessionStatus,
    AgentStage,
    AgentStageResult,
    AgentStageStatus,
)


def test_objective_rejects_repository_escape() -> None:
    with pytest.raises(ValidationError):
        AgentObjective(
            objective="Modify repository",
            repository_root=".",
            target_paths=("../outside.py",),
        )


def test_session_rejects_duplicate_stage_ids() -> None:
    stage = AgentStage(
        stage_id="stage-1",
        sequence=1,
        capability=AgentCapability.MISSION_PLANNING,
        name="Plan mission",
    )
    request = AgentRuntimeRequest(
        request_id="request-1",
        objective=AgentObjective(
            objective="Implement feature",
            repository_root=".",
        ),
    )

    with pytest.raises(ValidationError):
        AgentSession(
            session_id="session-1",
            request=request,
            status=AgentSessionStatus.CREATED,
            stages=(stage, stage),
        )


def test_session_rejects_unknown_stage_dependency() -> None:
    stage = AgentStage(
        stage_id="stage-1",
        sequence=1,
        capability=AgentCapability.MISSION_PLANNING,
        name="Plan mission",
        depends_on=("missing-stage",),
    )
    request = AgentRuntimeRequest(
        request_id="request-1",
        objective=AgentObjective(
            objective="Implement feature",
            repository_root=".",
        ),
    )

    with pytest.raises(ValidationError):
        AgentSession(
            session_id="session-1",
            request=request,
            status=AgentSessionStatus.CREATED,
            stages=(stage,),
        )


def test_terminal_stage_result_requires_completion_time() -> None:
    with pytest.raises(ValidationError):
        AgentStageResult(
            stage_id="stage-1",
            status=AgentStageStatus.SUCCEEDED,
            summary="completed",
        )


def test_terminal_stage_result_accepts_completion_time() -> None:
    result = AgentStageResult(
        stage_id="stage-1",
        status=AgentStageStatus.SUCCEEDED,
        summary="completed",
        completed_at=datetime.now(UTC),
    )

    assert result.status is AgentStageStatus.SUCCEEDED
'@

Write-Utf8NoBom "tests\test_agent_runtime_policies.py" @'
from datetime import UTC, datetime
from pathlib import Path

import pytest

from forge.agent_runtime.errors import (
    AgentRuntimeApprovalError,
    AgentRuntimePolicyError,
)
from forge.agent_runtime.models import (
    AgentApproval,
    AgentCapability,
    AgentObjective,
    AgentRuntimePolicy,
    AgentRuntimeRequest,
    ApprovalKind,
)
from forge.agent_runtime.policies import (
    require_approval,
    validate_request,
    validate_self_modification,
)


def test_policy_rejects_code_changes_by_default() -> None:
    request = AgentRuntimeRequest(
        request_id="request-1",
        objective=AgentObjective(
            objective="Implement feature",
            repository_root=".",
        ),
        allow_code_changes=True,
    )

    with pytest.raises(AgentRuntimePolicyError):
        validate_request(request, AgentRuntimePolicy())


def test_policy_rejects_disallowed_capability() -> None:
    request = AgentRuntimeRequest(
        request_id="request-1",
        objective=AgentObjective(
            objective="Implement feature",
            repository_root=".",
            requested_capabilities=(
                AgentCapability.AUTONOMOUS_REPAIR,
            ),
        ),
    )
    policy = AgentRuntimePolicy(
        allowed_capabilities=(
            AgentCapability.MISSION_PLANNING,
        )
    )

    with pytest.raises(AgentRuntimePolicyError):
        validate_request(request, policy)


def test_required_approval_is_enforced() -> None:
    with pytest.raises(AgentRuntimeApprovalError):
        require_approval(
            (),
            ApprovalKind.EDIT,
            AgentRuntimePolicy(),
        )


def test_latest_valid_approval_is_returned() -> None:
    approval = AgentApproval(
        approval_id="approval-1",
        kind=ApprovalKind.PLAN,
        approved=True,
        approved_by="operator",
        reason="approved",
        approved_at=datetime.now(UTC),
    )

    selected = require_approval(
        (approval,),
        ApprovalKind.PLAN,
        AgentRuntimePolicy(),
    )

    assert selected == approval


def test_self_modification_is_blocked(tmp_path: Path) -> None:
    runtime = tmp_path / "forge" / "agent_runtime"
    runtime.mkdir(parents=True)

    with pytest.raises(AgentRuntimePolicyError):
        validate_self_modification(
            tmp_path,
            ("forge/agent_runtime/models.py",),
            AgentRuntimePolicy(),
        )
'@

Write-Utf8NoBom "docs\agent_runtime\ARCHITECTURE.md" @'
# M3.8 Unified Agent Runtime Architecture

M3.8 connects existing Forge engineering capabilities into one controlled,
persistent, end-to-end agent runtime.

The runtime does not replace the existing modules. It coordinates them through
typed adapters, explicit stages, approval boundaries, checkpoints, telemetry,
and release evidence.

## Runtime layers

1. Contracts and policy
2. Capability adapters
3. Capability registry
4. Stage graph and lifecycle state machine
5. Session executor
6. Persistence and checkpoints
7. Recovery and telemetry
8. Reporting and CLI
9. Build-verification release gate

## Design principle

Every stage must be independently testable, auditable, resumable, and bounded.
No capability may bypass the approval or release gates.
'@

Write-Utf8NoBom "docs\agent_runtime\SPECIFICATION.md" @'
# M3.8 Unified Agent Runtime Specification

The runtime shall:

- accept one explicit engineering objective;
- create one deterministic agent request and session;
- orchestrate existing Forge capabilities through adapters;
- enforce stage dependencies and bounded execution;
- require human approval for plan, edit, repair, and release operations;
- persist recoverable checkpoints;
- emit structured telemetry;
- stop safely after required-stage failure;
- deny network access and self-modification by default;
- produce a final release recommendation backed by build-verification evidence.
'@

Write-Utf8NoBom "docs\agent_runtime\DATA_MODEL.md" @'
# M3.8 Unified Agent Runtime Data Model

Primary immutable models:

- `AgentObjective`
- `AgentRuntimeRequest`
- `AgentStage`
- `AgentStageResult`
- `AgentApproval`
- `AgentSession`
- `AgentCheckpoint`
- `AgentEvent`
- `AgentRuntimePolicy`

All lifecycle state uses explicit enumerations and deterministic identifiers.
'@

Write-Utf8NoBom "docs\agent_runtime\STATE_MACHINE.md" @'
# M3.8 Unified Agent Runtime State Machine

Primary lifecycle:

`created -> planning -> awaiting_approval -> executing -> validating`

Repair path:

`validating -> repairing -> validating`

Release path:

`validating -> verifying -> completed`

Control paths:

- any non-terminal state -> paused
- paused -> prior resumable state
- any non-terminal state -> cancelled
- required-stage failure -> failed
'@

Write-Utf8NoBom "docs\agent_runtime\SECURITY_MODEL.md" @'
# M3.8 Unified Agent Runtime Security Model

The runtime is fail-closed.

- Code changes are disabled by default.
- Network access is disabled by default.
- Self-modification is disabled by default.
- Plan, edit, repair, and release approvals are explicit.
- Capabilities are allow-listed.
- Stage counts and repair attempts are bounded.
- Repository-relative path escape is rejected.
- All stage outputs must be captured as evidence.
- The runtime never merges, tags, publishes, or deploys automatically.
'@

Write-Utf8NoBom "docs\agent_runtime\CAPABILITY_INTEGRATION.md" @'
# M3.8 Capability Integration

The unified runtime coordinates these existing Forge capabilities:

1. Repository discovery
2. Incremental project index
3. Engineering knowledge graph
4. Mission planning
5. Task management
6. Impact analysis
7. Safe change planning
8. Safe code editing
9. Validation and repair planning
10. Autonomous repair
11. Mission orchestration
12. Build verification and release gating

Each capability is exposed through a typed adapter and registered by capability
identifier. Adapters translate runtime stage input into the native subsystem
contract and normalize native output into `AgentStageResult`.
'@

Write-Utf8NoBom "docs\agent_runtime\ACCEPTANCE_CRITERIA.md" @'
# M3.8 Acceptance Criteria

Package 0 is accepted when:

- deterministic identifiers are implemented;
- immutable runtime contracts are implemented;
- repository-relative path escape is rejected;
- duplicate and invalid stage graphs are rejected;
- code changes are disabled by default;
- self-modification is disabled by default;
- capability allow-listing is enforced;
- approval requirements are enforced;
- lifecycle, security, architecture, and integration documentation exists;
- Ruff, MyPy, focused tests, and the complete test suite pass.
'@

Write-Host ""
Write-Host "M3.8 Package 0 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_agent_runtime_identifiers.py `
    .\tests\test_agent_runtime_models.py `
    .\tests\test_agent_runtime_policies.py `
    -p no:cacheprovider
Assert-CommandSuccess "M3.8 Package 0 tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M3.8 PACKAGE 0 COMPLETE" -ForegroundColor Green

git status --short
