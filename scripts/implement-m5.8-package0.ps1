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

    New-Item `
        -ItemType Directory `
        -Path $Directory `
        -Force | Out-Null

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

$ExpectedBranch = "feature/m5.8-autonomous-agent-runtime"
$CurrentBranch = git branch --show-current
Assert-CommandSuccess "Read current branch"

if ($CurrentBranch -ne $ExpectedBranch) {
    throw "M5.8 Package 0 must run on '$ExpectedBranch'. Current branch: '$CurrentBranch'."
}

Write-Utf8NoBom "forge\mission_runtime\errors.py" @'
"""Errors for the M5.8 Forge Mission Runtime."""

from __future__ import annotations


class MissionRuntimeError(Exception):
    """Base error for mission runtime failures."""


class MissionContractError(MissionRuntimeError):
    """Raised when a mission contract is invalid."""


class MissionStateError(MissionRuntimeError):
    """Raised when a mission state transition is invalid."""


class MissionPolicyError(MissionRuntimeError):
    """Raised when mission policy prevents an operation."""


class MissionScopeError(MissionRuntimeError):
    """Raised when mission scope and repository scope do not match."""


class MissionCapabilityError(MissionRuntimeError):
    """Raised when required capabilities are unavailable."""


class MissionApprovalError(MissionRuntimeError):
    """Raised when required approval is missing or invalid."""
'@

Write-Utf8NoBom "forge\mission_runtime\states.py" @'
"""State enumerations for the M5.8 Forge Mission Runtime."""

from __future__ import annotations

from enum import StrEnum


class MissionState(StrEnum):
    CREATED = "created"
    RESOLVING_WORKSPACE = "resolving_workspace"
    UNDERSTANDING_REPOSITORY = "understanding_repository"
    SELECTING_CAPABILITIES = "selecting_capabilities"
    RETRIEVING_CONTEXT = "retrieving_context"
    PLANNING = "planning"
    VALIDATING_PLAN = "validating_plan"
    AWAITING_PLAN_APPROVAL = "awaiting_plan_approval"
    APPROVED = "approved"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    RECOVERING = "recovering"
    DOCUMENTING = "documenting"
    GENERATING_REVIEW = "generating_review"
    AWAITING_FINAL_APPROVAL = "awaiting_final_approval"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MissionApprovalKind(StrEnum):
    PLAN = "plan"
    FINAL = "final"


class MissionApprovalDecision(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class MissionEvidenceKind(StrEnum):
    REPOSITORY = "repository"
    CAPABILITY = "capability"
    MEMORY = "memory"
    PLAN = "plan"
    APPROVAL = "approval"
    EXECUTION = "execution"
    VERIFICATION = "verification"
    DOCUMENTATION = "documentation"
    REVIEW = "review"
    RECOVERY = "recovery"


class MissionRisk(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MissionResultStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
'@

Write-Utf8NoBom "forge\mission_runtime\identifiers.py" @'
"""Deterministic identifiers for the M5.8 Mission Runtime."""

from __future__ import annotations

import hashlib
import json
from enum import Enum
from pathlib import Path
from typing import Any


def _normalize(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, dict):
        return {
            str(key): _normalize(item)
            for key, item in sorted(
                value.items(),
                key=lambda pair: str(pair[0]),
            )
        }
    if isinstance(value, list | tuple | set | frozenset):
        items = [_normalize(item) for item in value]
        if isinstance(value, set | frozenset):
            items = sorted(
                items,
                key=lambda item: json.dumps(
                    item,
                    sort_keys=True,
                    separators=(",", ":"),
                ),
            )
        return items
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    raise TypeError(
        f"Unsupported identifier value: {type(value)!r}"
    )


def deterministic_mission_identifier(
    prefix: str,
    payload: dict[str, Any],
) -> str:
    canonical = json.dumps(
        _normalize(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    digest = hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()[:24]
    return f"{prefix}-{digest}"


def mission_request_identifier(
    payload: dict[str, Any],
) -> str:
    return deterministic_mission_identifier(
        "mission-request",
        payload,
    )


def mission_session_identifier(
    payload: dict[str, Any],
) -> str:
    return deterministic_mission_identifier(
        "mission-session",
        payload,
    )


def mission_checkpoint_identifier(
    payload: dict[str, Any],
) -> str:
    return deterministic_mission_identifier(
        "mission-checkpoint",
        payload,
    )


def mission_approval_identifier(
    payload: dict[str, Any],
) -> str:
    return deterministic_mission_identifier(
        "mission-approval",
        payload,
    )


def mission_evidence_identifier(
    payload: dict[str, Any],
) -> str:
    return deterministic_mission_identifier(
        "mission-evidence",
        payload,
    )


def mission_result_identifier(
    payload: dict[str, Any],
) -> str:
    return deterministic_mission_identifier(
        "mission-result",
        payload,
    )
'@

Write-Utf8NoBom "forge\mission_runtime\policies.py" @'
"""Policies for the M5.8 Forge Mission Runtime."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class MissionLimits(BaseModel):
    model_config = ConfigDict(frozen=True)

    maximum_state_transitions: int = Field(
        default=100,
        ge=1,
        le=1000,
    )
    maximum_recovery_cycles: int = Field(
        default=3,
        ge=0,
        le=20,
    )
    maximum_selected_capabilities: int = Field(
        default=50,
        ge=1,
        le=500,
    )
    maximum_evidence_items: int = Field(
        default=2000,
        ge=1,
        le=20000,
    )


class MissionApprovalPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    require_plan_approval_for_high_risk: bool = True
    require_plan_approval_for_destructive_changes: bool = True
    require_final_approval_for_merge_worthy_work: bool = True
    require_final_approval_for_release: bool = True


class MissionSafetyPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    require_active_workspace: bool = True
    require_repository_scope_match: bool = True
    require_registered_capabilities: bool = True
    require_verification_before_completion: bool = True
    stop_on_blocking_failure: bool = True
    allow_unrestricted_git_operations: bool = False
    allow_self_modification: bool = False
    allow_scope_expansion_without_approval: bool = False


class MissionRuntimePolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    limits: MissionLimits = Field(
        default_factory=MissionLimits
    )
    approvals: MissionApprovalPolicy = Field(
        default_factory=MissionApprovalPolicy
    )
    safety: MissionSafetyPolicy = Field(
        default_factory=MissionSafetyPolicy
    )
'@

Write-Utf8NoBom "forge\mission_runtime\models.py" @'
"""Immutable contracts for the M5.8 Forge Mission Runtime."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, model_validator

from forge.mission_runtime.errors import MissionContractError
from forge.mission_runtime.states import (
    MissionApprovalDecision,
    MissionApprovalKind,
    MissionEvidenceKind,
    MissionResultStatus,
    MissionRisk,
    MissionState,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MissionRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    request_id: str
    workspace_id: str
    repository_root: str
    statement: str
    requested_by: str
    risk_tolerance: MissionRisk = MissionRisk.MEDIUM
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_request(self) -> "MissionRequest":
        if not self.workspace_id.strip():
            raise MissionContractError(
                "Workspace ID cannot be empty."
            )
        if not self.repository_root.strip():
            raise MissionContractError(
                "Repository root cannot be empty."
            )
        if not self.statement.strip():
            raise MissionContractError(
                "Mission statement cannot be empty."
            )
        if not self.requested_by.strip():
            raise MissionContractError(
                "Mission requester cannot be empty."
            )
        return self


class MissionApproval(BaseModel):
    model_config = ConfigDict(frozen=True)

    approval_id: str
    session_id: str
    kind: MissionApprovalKind
    decision: MissionApprovalDecision
    decided_by: str | None = None
    rationale: str | None = None
    scope: tuple[str, ...] = ()
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_approval(self) -> "MissionApproval":
        if (
            self.decision
            is not MissionApprovalDecision.PENDING
            and not self.decided_by
        ):
            raise MissionContractError(
                "Decided approval requires an approver."
            )
        if (
            self.decision
            is not MissionApprovalDecision.PENDING
            and not self.rationale
        ):
            raise MissionContractError(
                "Decided approval requires rationale."
            )
        return self


class MissionCheckpoint(BaseModel):
    model_config = ConfigDict(frozen=True)

    checkpoint_id: str
    session_id: str
    state: MissionState
    repository_fingerprint: str
    planning_plan_id: str | None = None
    execution_run_id: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class MissionEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    evidence_id: str
    session_id: str
    kind: MissionEvidenceKind
    references: tuple[str, ...]
    summary: str
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_evidence(self) -> "MissionEvidence":
        if not self.references:
            raise MissionContractError(
                "Mission evidence requires references."
            )
        if not self.summary.strip():
            raise MissionContractError(
                "Mission evidence summary cannot be empty."
            )
        return self


class MissionSession(BaseModel):
    model_config = ConfigDict(frozen=True)

    session_id: str
    request_id: str
    workspace_id: str
    repository_root: str
    repository_fingerprint: str
    state: MissionState = MissionState.CREATED
    detected_technologies: tuple[str, ...] = ()
    selected_capabilities: tuple[str, ...] = ()
    memory_query_ids: tuple[str, ...] = ()
    planning_request_id: str | None = None
    planning_plan_id: str | None = None
    plan_approval_id: str | None = None
    execution_run_ids: tuple[str, ...] = ()
    verification_references: tuple[str, ...] = ()
    documentation_references: tuple[str, ...] = ()
    review_package_reference: str | None = None
    final_approval_id: str | None = None
    recovery_count: int = Field(default=0, ge=0)
    failure_reason: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_session(self) -> "MissionSession":
        if not self.repository_root.strip():
            raise MissionContractError(
                "Mission repository root cannot be empty."
            )
        if not self.repository_fingerprint.strip():
            raise MissionContractError(
                "Repository fingerprint cannot be empty."
            )
        if (
            self.state is MissionState.COMPLETED
            and not self.verification_references
        ):
            raise MissionContractError(
                "Completed mission requires verification evidence."
            )
        return self


class MissionResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    result_id: str
    session_id: str
    status: MissionResultStatus
    summary: str
    evidence_ids: tuple[str, ...] = ()
    review_package_reference: str | None = None
    completed_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_result(self) -> "MissionResult":
        if not self.summary.strip():
            raise MissionContractError(
                "Mission result summary cannot be empty."
            )
        return self
'@

Write-Utf8NoBom "forge\mission_runtime\__init__.py" @'
"""M5.8 Forge Mission Runtime contracts."""

from forge.mission_runtime.errors import (
    MissionApprovalError,
    MissionCapabilityError,
    MissionContractError,
    MissionPolicyError,
    MissionRuntimeError,
    MissionScopeError,
    MissionStateError,
)
from forge.mission_runtime.identifiers import (
    deterministic_mission_identifier,
    mission_approval_identifier,
    mission_checkpoint_identifier,
    mission_evidence_identifier,
    mission_request_identifier,
    mission_result_identifier,
    mission_session_identifier,
)
from forge.mission_runtime.models import (
    MissionApproval,
    MissionCheckpoint,
    MissionEvidence,
    MissionRequest,
    MissionResult,
    MissionSession,
)
from forge.mission_runtime.policies import (
    MissionApprovalPolicy,
    MissionLimits,
    MissionRuntimePolicy,
    MissionSafetyPolicy,
)
from forge.mission_runtime.states import (
    MissionApprovalDecision,
    MissionApprovalKind,
    MissionEvidenceKind,
    MissionResultStatus,
    MissionRisk,
    MissionState,
)

__all__ = [
    "MissionApproval",
    "MissionApprovalDecision",
    "MissionApprovalError",
    "MissionApprovalKind",
    "MissionApprovalPolicy",
    "MissionCapabilityError",
    "MissionCheckpoint",
    "MissionContractError",
    "MissionEvidence",
    "MissionEvidenceKind",
    "MissionLimits",
    "MissionPolicyError",
    "MissionRequest",
    "MissionResult",
    "MissionResultStatus",
    "MissionRisk",
    "MissionRuntimeError",
    "MissionRuntimePolicy",
    "MissionSafetyPolicy",
    "MissionScopeError",
    "MissionSession",
    "MissionState",
    "MissionStateError",
    "deterministic_mission_identifier",
    "mission_approval_identifier",
    "mission_checkpoint_identifier",
    "mission_evidence_identifier",
    "mission_request_identifier",
    "mission_result_identifier",
    "mission_session_identifier",
]
'@

Write-Utf8NoBom "tests\test_mission_runtime_identifiers.py" @'
from forge.mission_runtime.identifiers import (
    mission_request_identifier,
    mission_session_identifier,
)


def test_mission_identifiers_are_deterministic() -> None:
    payload = {
        "workspace_id": "workspace-1",
        "paths": {"b.py", "a.py"},
    }

    assert mission_request_identifier(
        payload
    ) == mission_request_identifier(payload)


def test_mission_identifier_prefixes_are_distinct() -> None:
    payload = {"mission": "complete procurement"}

    assert mission_request_identifier(
        payload
    ).startswith("mission-request-")

    assert mission_session_identifier(
        payload
    ).startswith("mission-session-")
'@

Write-Utf8NoBom "tests\test_mission_runtime_states.py" @'
from forge.mission_runtime.states import (
    MissionApprovalDecision,
    MissionEvidenceKind,
    MissionResultStatus,
    MissionState,
)


def test_mission_state_values_are_stable() -> None:
    assert MissionState.PLANNING.value == "planning"
    assert (
        MissionState.AWAITING_PLAN_APPROVAL.value
        == "awaiting_plan_approval"
    )
    assert (
        MissionEvidenceKind.VERIFICATION.value
        == "verification"
    )
    assert (
        MissionApprovalDecision.APPROVED.value
        == "approved"
    )
    assert (
        MissionResultStatus.COMPLETED.value
        == "completed"
    )
'@

Write-Utf8NoBom "tests\test_mission_runtime_policies.py" @'
from forge.mission_runtime.policies import MissionRuntimePolicy


def test_default_mission_policy_is_safe() -> None:
    policy = MissionRuntimePolicy()

    assert policy.safety.require_active_workspace
    assert policy.safety.require_registered_capabilities
    assert policy.safety.require_verification_before_completion
    assert not policy.safety.allow_unrestricted_git_operations
    assert not policy.safety.allow_self_modification
    assert (
        policy.approvals
        .require_plan_approval_for_high_risk
    )
'@

Write-Utf8NoBom "tests\test_mission_runtime_models.py" @'
import pytest

from forge.mission_runtime.errors import MissionContractError
from forge.mission_runtime.models import (
    MissionApproval,
    MissionEvidence,
    MissionRequest,
    MissionSession,
)
from forge.mission_runtime.states import (
    MissionApprovalDecision,
    MissionApprovalKind,
    MissionEvidenceKind,
    MissionState,
)


def test_request_rejects_empty_statement() -> None:
    with pytest.raises(MissionContractError):
        MissionRequest(
            request_id="request-1",
            workspace_id="workspace-1",
            repository_root="repository",
            statement="",
            requested_by="Aerion",
        )


def test_decided_approval_requires_approver() -> None:
    with pytest.raises(MissionContractError):
        MissionApproval(
            approval_id="approval-1",
            session_id="session-1",
            kind=MissionApprovalKind.PLAN,
            decision=MissionApprovalDecision.APPROVED,
            rationale="Plan approved.",
        )


def test_evidence_requires_references() -> None:
    with pytest.raises(MissionContractError):
        MissionEvidence(
            evidence_id="evidence-1",
            session_id="session-1",
            kind=MissionEvidenceKind.PLAN,
            references=(),
            summary="Plan generated.",
        )


def test_completed_session_requires_verification() -> None:
    with pytest.raises(MissionContractError):
        MissionSession(
            session_id="session-1",
            request_id="request-1",
            workspace_id="workspace-1",
            repository_root="repository",
            repository_fingerprint="fingerprint",
            state=MissionState.COMPLETED,
        )
'@

Write-Host ""
Write-Host "M5.8 Package 0 files written. Running validation..." `
    -ForegroundColor Cyan

python -m ruff check forge tests --fix
Assert-CommandSuccess "Ruff fix"

python -m ruff check forge tests
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_mission_runtime_identifiers.py `
    .\tests\test_mission_runtime_states.py `
    .\tests\test_mission_runtime_policies.py `
    .\tests\test_mission_runtime_models.py `
    -p no:cacheprovider
Assert-CommandSuccess "M5.8 Package 0 focused tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full repository tests"

Write-Host ""
Write-Host "M5.8 PACKAGE 0 COMPLETE" -ForegroundColor Green

git status --short
