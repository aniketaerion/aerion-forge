"""Approval lifecycle and scope validation."""

from __future__ import annotations

from datetime import UTC, datetime

from forge.autonomous_runtime.errors import MissionPolicyError
from forge.autonomous_runtime.models import ApprovalDecision
from forge.autonomous_runtime.states import AuthorityLevel


def utc_now() -> datetime:
    return datetime.now(UTC)


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