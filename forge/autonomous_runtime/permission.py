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