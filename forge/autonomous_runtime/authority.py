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