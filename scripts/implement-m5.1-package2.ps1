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

$ExpectedBranch = "feature/m5.1-autonomous-runtime-architecture"
$CurrentBranch = git branch --show-current
Assert-CommandSuccess "Read current branch"

if ($CurrentBranch -ne $ExpectedBranch) {
    throw "M5.1 Package 2 must run on '$ExpectedBranch'. Current branch: '$CurrentBranch'."
}

Write-Utf8NoBom "forge\autonomous_runtime\authority.py" @'
"""Authority evaluation for autonomous-runtime actions."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_runtime.errors import MissionPolicyError
from forge.autonomous_runtime.models import AutonomousMission
from forge.autonomous_runtime.policies import AuthorityPolicy
from forge.autonomous_runtime.states import AuthorityLevel, RiskClass


@dataclass(frozen=True, slots=True)
class AuthorityRequest:
    """Authority required for one proposed action."""

    required_authority: AuthorityLevel
    risk_class: RiskClass
    scope: tuple[str, ...] = ()
    action_kind: str = "unspecified"


@dataclass(frozen=True, slots=True)
class AuthorityEvaluation:
    """Deterministic result of authority policy evaluation."""

    allowed: bool
    approval_required: bool
    reason: str
    effective_ceiling: AuthorityLevel


def evaluate_authority(
    mission: AutonomousMission,
    request: AuthorityRequest,
    *,
    policy: AuthorityPolicy | None = None,
) -> AuthorityEvaluation:
    """Evaluate an action against mission and runtime authority."""
    effective_policy = policy or AuthorityPolicy()

    if request.required_authority > mission.request.requested_authority:
        return AuthorityEvaluation(
            allowed=False,
            approval_required=True,
            reason="Action exceeds authority requested by the mission.",
            effective_ceiling=mission.request.requested_authority,
        )

    if request.required_authority > mission.granted_authority:
        return AuthorityEvaluation(
            allowed=False,
            approval_required=True,
            reason="Action exceeds currently granted mission authority.",
            effective_ceiling=mission.granted_authority,
        )

    approval_required = (
        request.required_authority
        >= effective_policy.explicit_approval_from
        or request.risk_class >= effective_policy.high_risk_from
    )

    return AuthorityEvaluation(
        allowed=True,
        approval_required=approval_required,
        reason=(
            "Explicit approval required by authority or risk policy."
            if approval_required
            else "Action is within granted authority and policy."
        ),
        effective_ceiling=mission.granted_authority,
    )


def assert_authority_allowed(
    mission: AutonomousMission,
    request: AuthorityRequest,
    *,
    policy: AuthorityPolicy | None = None,
) -> AuthorityEvaluation:
    """Return evaluation or raise when authority is insufficient."""
    evaluation = evaluate_authority(
        mission,
        request,
        policy=policy,
    )
    if not evaluation.allowed:
        raise MissionPolicyError(evaluation.reason)
    return evaluation
'@

Write-Utf8NoBom "forge\autonomous_runtime\approvals.py" @'
"""Approval lifecycle and scope validation."""

from __future__ import annotations

from datetime import datetime, timezone

from forge.autonomous_runtime.errors import MissionPolicyError
from forge.autonomous_runtime.models import ApprovalDecision
from forge.autonomous_runtime.states import AuthorityLevel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def approval_is_active(
    approval: ApprovalDecision,
    *,
    at: datetime | None = None,
) -> bool:
    """Return whether an approval is active at a point in time."""
    moment = at or utc_now()
    return (
        approval.revoked_at is None
        and (
            approval.expires_at is None
            or approval.expires_at > moment
        )
    )


def approval_covers_scope(
    approval: ApprovalDecision,
    requested_scope: tuple[str, ...],
) -> bool:
    """Return whether approval scope covers all requested paths."""
    if not requested_scope:
        return True
    if not approval.scope:
        return False

    approved = set(approval.scope)
    return set(requested_scope).issubset(approved)


def approval_grants_authority(
    approval: ApprovalDecision,
    required: AuthorityLevel,
) -> bool:
    """Return whether approval grants the required authority."""
    return approval.authority_granted >= required


def assert_approval_valid(
    approval: ApprovalDecision,
    *,
    mission_id: str,
    required_authority: AuthorityLevel,
    requested_scope: tuple[str, ...] = (),
    at: datetime | None = None,
) -> None:
    """Validate approval identity, activity, authority, and scope."""
    if approval.mission_id != mission_id:
        raise MissionPolicyError(
            "Approval belongs to a different mission."
        )
    if not approval_is_active(approval, at=at):
        raise MissionPolicyError(
            "Approval is expired or revoked."
        )
    if not approval_grants_authority(
        approval,
        required_authority,
    ):
        raise MissionPolicyError(
            "Approval does not grant required authority."
        )
    if not approval_covers_scope(
        approval,
        requested_scope,
    ):
        raise MissionPolicyError(
            "Approval does not cover requested scope."
        )
'@

Write-Utf8NoBom "forge\autonomous_runtime\risk.py" @'
"""Deterministic risk classification for autonomous actions."""

from __future__ import annotations

from types import MappingProxyType
from typing import Final, Mapping

from forge.autonomous_runtime.states import RiskClass


_ACTION_RISK: dict[str, RiskClass] = {
    "read_file": RiskClass.R0_READ_ONLY,
    "search_repository": RiskClass.R0_READ_ONLY,
    "create_plan": RiskClass.R1_LOW,
    "write_documentation": RiskClass.R1_LOW,
    "modify_tests": RiskClass.R2_MODERATE,
    "apply_patch": RiskClass.R2_MODERATE,
    "modify_public_api": RiskClass.R3_HIGH,
    "modify_authentication": RiskClass.R3_HIGH,
    "modify_financial_logic": RiskClass.R3_HIGH,
    "modify_safety_logic": RiskClass.R3_HIGH,
    "modify_architecture": RiskClass.R3_HIGH,
    "create_commit": RiskClass.R4_CRITICAL,
    "push_branch": RiskClass.R4_CRITICAL,
    "database_migration": RiskClass.R4_CRITICAL,
    "merge_branch": RiskClass.R4_CRITICAL,
    "create_release": RiskClass.R4_CRITICAL,
    "production_control": RiskClass.R5_HUMAN_CONTROLLED,
}

ACTION_RISK: Final[Mapping[str, RiskClass]] = MappingProxyType(
    _ACTION_RISK
)


def classify_action_risk(
    action_kind: str,
    *,
    fallback: RiskClass = RiskClass.R3_HIGH,
) -> RiskClass:
    """Classify action risk conservatively."""
    return ACTION_RISK.get(action_kind, fallback)


def maximum_risk(
    risks: tuple[RiskClass, ...],
) -> RiskClass:
    """Return the highest risk in a collection."""
    return max(risks, default=RiskClass.R0_READ_ONLY)
'@

Write-Utf8NoBom "forge\autonomous_runtime\permission.py" @'
"""Unified permission decision service."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_runtime.approvals import (
    assert_approval_valid,
)
from forge.autonomous_runtime.authority import (
    AuthorityRequest,
    evaluate_authority,
)
from forge.autonomous_runtime.errors import MissionPolicyError
from forge.autonomous_runtime.models import (
    ApprovalDecision,
    AutonomousMission,
)
from forge.autonomous_runtime.policies import AuthorityPolicy
from forge.autonomous_runtime.states import AuthorityLevel, RiskClass


@dataclass(frozen=True, slots=True)
class PermissionDecision:
    """Final permission decision for one action."""

    permitted: bool
    approval_required: bool
    reason: str


def decide_permission(
    mission: AutonomousMission,
    *,
    required_authority: AuthorityLevel,
    risk_class: RiskClass,
    scope: tuple[str, ...] = (),
    action_kind: str = "unspecified",
    approval: ApprovalDecision | None = None,
    policy: AuthorityPolicy | None = None,
) -> PermissionDecision:
    """Evaluate mission authority and optional approval."""
    evaluation = evaluate_authority(
        mission,
        AuthorityRequest(
            required_authority=required_authority,
            risk_class=risk_class,
            scope=scope,
            action_kind=action_kind,
        ),
        policy=policy,
    )

    if not evaluation.allowed:
        return PermissionDecision(
            permitted=False,
            approval_required=True,
            reason=evaluation.reason,
        )

    if not evaluation.approval_required:
        return PermissionDecision(
            permitted=True,
            approval_required=False,
            reason=evaluation.reason,
        )

    if approval is None:
        return PermissionDecision(
            permitted=False,
            approval_required=True,
            reason="Explicit approval is required.",
        )

    try:
        assert_approval_valid(
            approval,
            mission_id=mission.mission_id,
            required_authority=required_authority,
            requested_scope=scope,
        )
    except MissionPolicyError as exc:
        return PermissionDecision(
            permitted=False,
            approval_required=True,
            reason=str(exc),
        )

    return PermissionDecision(
        permitted=True,
        approval_required=True,
        reason="Explicit approval is valid.",
    )


def assert_permission(
    mission: AutonomousMission,
    *,
    required_authority: AuthorityLevel,
    risk_class: RiskClass,
    scope: tuple[str, ...] = (),
    action_kind: str = "unspecified",
    approval: ApprovalDecision | None = None,
    policy: AuthorityPolicy | None = None,
) -> PermissionDecision:
    """Return permission or raise on denial."""
    decision = decide_permission(
        mission,
        required_authority=required_authority,
        risk_class=risk_class,
        scope=scope,
        action_kind=action_kind,
        approval=approval,
        policy=policy,
    )
    if not decision.permitted:
        raise MissionPolicyError(decision.reason)
    return decision
'@

Write-Utf8NoBom "tests\test_autonomous_runtime_authority.py" @'
from forge.autonomous_runtime.authority import (
    AuthorityRequest,
    evaluate_authority,
)
from forge.autonomous_runtime.models import (
    AutonomousMission,
    MissionRequest,
)
from forge.autonomous_runtime.states import (
    AuthorityLevel,
    RiskClass,
)


def mission() -> AutonomousMission:
    return AutonomousMission(
        mission_id="mission-1",
        request=MissionRequest(
            request_id="request-1",
            objective="Evaluate authority.",
            repository_root="repository",
            requested_authority=AuthorityLevel.A4_COMMIT,
            requested_by="Aerion",
        ),
        granted_authority=AuthorityLevel.A4_COMMIT,
    )


def test_low_risk_modify_is_allowed_without_explicit_approval() -> None:
    result = evaluate_authority(
        mission(),
        AuthorityRequest(
            required_authority=AuthorityLevel.A2_MODIFY,
            risk_class=RiskClass.R2_MODERATE,
        ),
    )

    assert result.allowed
    assert not result.approval_required


def test_commit_requires_explicit_approval() -> None:
    result = evaluate_authority(
        mission(),
        AuthorityRequest(
            required_authority=AuthorityLevel.A4_COMMIT,
            risk_class=RiskClass.R4_CRITICAL,
        ),
    )

    assert result.allowed
    assert result.approval_required
'@

Write-Utf8NoBom "tests\test_autonomous_runtime_approvals.py" @'
from datetime import timedelta

import pytest

from forge.autonomous_runtime.approvals import (
    approval_covers_scope,
    approval_is_active,
    assert_approval_valid,
)
from forge.autonomous_runtime.errors import MissionPolicyError
from forge.autonomous_runtime.models import ApprovalDecision, utc_now
from forge.autonomous_runtime.states import AuthorityLevel


def approval() -> ApprovalDecision:
    return ApprovalDecision(
        approval_id="approval-1",
        mission_id="mission-1",
        decision="approve",
        authority_granted=AuthorityLevel.A4_COMMIT,
        scope=("forge/autonomous_runtime",),
        approved_by="Aerion",
        expires_at=utc_now() + timedelta(minutes=5),
    )


def test_active_approval_covers_scope() -> None:
    item = approval()

    assert approval_is_active(item)
    assert approval_covers_scope(
        item,
        ("forge/autonomous_runtime",),
    )


def test_wrong_mission_is_rejected() -> None:
    with pytest.raises(MissionPolicyError):
        assert_approval_valid(
            approval(),
            mission_id="mission-2",
            required_authority=AuthorityLevel.A4_COMMIT,
            requested_scope=("forge/autonomous_runtime",),
        )
'@

Write-Utf8NoBom "tests\test_autonomous_runtime_risk.py" @'
from forge.autonomous_runtime.risk import (
    classify_action_risk,
    maximum_risk,
)
from forge.autonomous_runtime.states import RiskClass


def test_known_action_risk_is_classified() -> None:
    assert (
        classify_action_risk("create_release")
        is RiskClass.R4_CRITICAL
    )


def test_unknown_action_defaults_high() -> None:
    assert (
        classify_action_risk("unknown_action")
        is RiskClass.R3_HIGH
    )


def test_maximum_risk_returns_highest_value() -> None:
    assert maximum_risk(
        (
            RiskClass.R1_LOW,
            RiskClass.R4_CRITICAL,
            RiskClass.R2_MODERATE,
        )
    ) is RiskClass.R4_CRITICAL
'@

Write-Utf8NoBom "tests\test_autonomous_runtime_permission.py" @'
from datetime import timedelta

from forge.autonomous_runtime.models import (
    ApprovalDecision,
    AutonomousMission,
    MissionRequest,
    utc_now,
)
from forge.autonomous_runtime.permission import decide_permission
from forge.autonomous_runtime.states import (
    AuthorityLevel,
    RiskClass,
)


def mission() -> AutonomousMission:
    return AutonomousMission(
        mission_id="mission-1",
        request=MissionRequest(
            request_id="request-1",
            objective="Evaluate permission.",
            repository_root="repository",
            requested_authority=AuthorityLevel.A4_COMMIT,
            requested_by="Aerion",
        ),
        granted_authority=AuthorityLevel.A4_COMMIT,
    )


def test_high_risk_action_is_denied_without_approval() -> None:
    decision = decide_permission(
        mission(),
        required_authority=AuthorityLevel.A4_COMMIT,
        risk_class=RiskClass.R4_CRITICAL,
        scope=("forge/autonomous_runtime",),
        action_kind="create_commit",
    )

    assert not decision.permitted
    assert decision.approval_required


def test_valid_approval_permits_high_risk_action() -> None:
    item = ApprovalDecision(
        approval_id="approval-1",
        mission_id="mission-1",
        decision="approve",
        authority_granted=AuthorityLevel.A4_COMMIT,
        scope=("forge/autonomous_runtime",),
        approved_by="Aerion",
        expires_at=utc_now() + timedelta(minutes=5),
    )

    decision = decide_permission(
        mission(),
        required_authority=AuthorityLevel.A4_COMMIT,
        risk_class=RiskClass.R4_CRITICAL,
        scope=("forge/autonomous_runtime",),
        action_kind="create_commit",
        approval=item,
    )

    assert decision.permitted
    assert decision.approval_required
'@

Write-Host ""
Write-Host "M5.1 Package 2 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check . --fix
Assert-CommandSuccess "Ruff fix"

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_autonomous_runtime_authority.py `
    .\tests\test_autonomous_runtime_approvals.py `
    .\tests\test_autonomous_runtime_risk.py `
    .\tests\test_autonomous_runtime_permission.py `
    -p no:cacheprovider
Assert-CommandSuccess "M5.1 Package 2 focused tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M5.1 PACKAGE 2 COMPLETE" -ForegroundColor Green

git status --short