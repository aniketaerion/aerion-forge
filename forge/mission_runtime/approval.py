"""Mission-level approval orchestration."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_planning.models import PlanningPlan
from forge.autonomous_planning.states import PlanningRisk
from forge.mission_runtime.errors import MissionApprovalError
from forge.mission_runtime.models import MissionApproval
from forge.mission_runtime.policies import MissionRuntimePolicy
from forge.mission_runtime.states import (
    MissionApprovalDecision,
    MissionApprovalKind,
)


@dataclass(frozen=True, slots=True)
class MissionApprovalRequirement:
    required: bool
    rationale: tuple[str, ...]


def plan_approval_requirement(
    *,
    plan: PlanningPlan,
    policy: MissionRuntimePolicy,
) -> MissionApprovalRequirement:
    reasons: list[str] = []

    if plan.requires_approval:
        reasons.append(
            "Planning engine marked the plan as requiring approval."
        )

    if (
        policy.approvals.require_plan_approval_for_high_risk
        and plan.risk
        in {PlanningRisk.HIGH, PlanningRisk.CRITICAL}
    ):
        reasons.append(
            "High-risk mission plan requires human approval."
        )

    if (
        policy.approvals
        .require_plan_approval_for_destructive_changes
        and any(step.destructive for step in plan.steps)
    ):
        reasons.append(
            "Destructive plan step requires human approval."
        )

    return MissionApprovalRequirement(
        required=bool(reasons),
        rationale=tuple(reasons),
    )


def assert_plan_approved(
    *,
    requirement: MissionApprovalRequirement,
    approval: MissionApproval | None,
) -> None:
    if not requirement.required:
        return

    if approval is None:
        raise MissionApprovalError(
            "Mission plan requires approval before execution."
        )

    if approval.kind is not MissionApprovalKind.PLAN:
        raise MissionApprovalError(
            "Mission approval is not a plan approval."
        )

    if (
        approval.decision
        is not MissionApprovalDecision.APPROVED
    ):
        raise MissionApprovalError(
            "Mission plan approval has not been granted."
        )