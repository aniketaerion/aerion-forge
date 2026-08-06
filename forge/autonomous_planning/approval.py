"""Plan approval and rejection controls."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from forge.autonomous_planning.errors import (
    PlanningStateError,
)
from forge.autonomous_planning.models import PlanningPlan
from forge.autonomous_planning.states import PlanningState


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class PlanningApprovalDecision:
    """Recorded human or policy approval decision."""

    plan_id: str
    approved: bool
    decided_by: str
    rationale: str
    decided_at: datetime


def approve_plan(
    *,
    plan: PlanningPlan,
    decided_by: str,
    rationale: str,
) -> tuple[PlanningPlan, PlanningApprovalDecision]:
    """Approve a plan that is awaiting approval."""
    if plan.state is not PlanningState.AWAITING_APPROVAL:
        raise PlanningStateError(
            "Only plans awaiting approval can be approved."
        )

    if not decided_by.strip():
        raise ValueError("Approver cannot be empty.")

    if not rationale.strip():
        raise ValueError("Approval rationale cannot be empty.")

    now = utc_now()
    approved = plan.model_copy(
        update={
            "state": PlanningState.READY,
            "updated_at": now,
        }
    )
    decision = PlanningApprovalDecision(
        plan_id=plan.plan_id,
        approved=True,
        decided_by=decided_by,
        rationale=rationale,
        decided_at=now,
    )
    return approved, decision


def reject_plan(
    *,
    plan: PlanningPlan,
    decided_by: str,
    rationale: str,
) -> tuple[PlanningPlan, PlanningApprovalDecision]:
    """Reject a plan that is awaiting approval."""
    if plan.state is not PlanningState.AWAITING_APPROVAL:
        raise PlanningStateError(
            "Only plans awaiting approval can be rejected."
        )

    if not decided_by.strip():
        raise ValueError("Rejector cannot be empty.")

    if not rationale.strip():
        raise ValueError("Rejection rationale cannot be empty.")

    now = utc_now()
    rejected = plan.model_copy(
        update={
            "state": PlanningState.REJECTED,
            "updated_at": now,
        }
    )
    decision = PlanningApprovalDecision(
        plan_id=plan.plan_id,
        approved=False,
        decided_by=decided_by,
        rationale=rationale,
        decided_at=now,
    )
    return rejected, decision