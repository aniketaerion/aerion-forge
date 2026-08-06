import pytest

from forge.autonomous_planning.approval import (
    approve_plan,
    reject_plan,
)
from forge.autonomous_planning.errors import (
    PlanningStateError,
)
from forge.autonomous_planning.models import (
    PlanningPlan,
    PlanningStep,
)
from forge.autonomous_planning.states import (
    PlanningState,
    StepKind,
)


def plan(state: PlanningState) -> PlanningPlan:
    return PlanningPlan(
        plan_id="plan-1",
        request_id="request-1",
        state=state,
        summary="Plan.",
        steps=(
            PlanningStep(
                step_id="step-1",
                sequence=1,
                name="Validate",
                description="Validate repository behaviour.",
                kind=StepKind.VALIDATION,
            ),
        ),
    )


def test_approve_moves_plan_to_ready() -> None:
    approved, decision = approve_plan(
        plan=plan(PlanningState.AWAITING_APPROVAL),
        decided_by="Aerion",
        rationale="Risk accepted.",
    )

    assert approved.state is PlanningState.READY
    assert decision.approved


def test_reject_moves_plan_to_rejected() -> None:
    rejected, decision = reject_plan(
        plan=plan(PlanningState.AWAITING_APPROVAL),
        decided_by="Aerion",
        rationale="Risk too high.",
    )

    assert rejected.state is PlanningState.REJECTED
    assert not decision.approved


def test_ready_plan_cannot_be_approved_again() -> None:
    with pytest.raises(PlanningStateError):
        approve_plan(
            plan=plan(PlanningState.READY),
            decided_by="Aerion",
            rationale="Already ready.",
        )