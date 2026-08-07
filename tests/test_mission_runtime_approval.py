import pytest

from forge.autonomous_planning.models import (
    PlanningPlan,
    PlanningStep,
)
from forge.autonomous_planning.states import (
    ApprovalRequirement,
    PlanningRisk,
    StepKind,
)
from forge.mission_runtime.approval import (
    assert_plan_approved,
    plan_approval_requirement,
)
from forge.mission_runtime.errors import MissionApprovalError
from forge.mission_runtime.models import MissionApproval
from forge.mission_runtime.policies import MissionRuntimePolicy
from forge.mission_runtime.states import (
    MissionApprovalDecision,
    MissionApprovalKind,
)


def plan(
    *,
    risk: PlanningRisk = PlanningRisk.LOW,
    destructive: bool = False,
    requires_approval: bool = False,
) -> PlanningPlan:
    return PlanningPlan(
        plan_id="plan-1",
        request_id="request-1",
        summary="Test plan.",
        steps=(
            PlanningStep(
                step_id="step-1",
                sequence=1,
                name="Change",
                description="Perform approved change.",
                kind=StepKind.CODE_CHANGE,
                risk=risk,
                destructive=destructive,
                approval_requirement=(
                    ApprovalRequirement.PLAN
                    if destructive
                    else ApprovalRequirement.NONE
                ),
            ),
        ),
        risk=risk,
        requires_approval=requires_approval,
    )


def test_high_risk_plan_requires_approval() -> None:
    requirement = plan_approval_requirement(
        plan=plan(risk=PlanningRisk.HIGH),
        policy=MissionRuntimePolicy(),
    )

    assert requirement.required


def test_required_plan_without_approval_is_blocked() -> None:
    requirement = plan_approval_requirement(
        plan=plan(requires_approval=True),
        policy=MissionRuntimePolicy(),
    )

    with pytest.raises(MissionApprovalError):
        assert_plan_approved(
            requirement=requirement,
            approval=None,
        )


def test_approved_plan_passes_gate() -> None:
    requirement = plan_approval_requirement(
        plan=plan(requires_approval=True),
        policy=MissionRuntimePolicy(),
    )
    approval = MissionApproval(
        approval_id="approval-1",
        session_id="session-1",
        kind=MissionApprovalKind.PLAN,
        decision=MissionApprovalDecision.APPROVED,
        decided_by="reviewer",
        rationale="Approved.",
    )

    assert_plan_approved(
        requirement=requirement,
        approval=approval,
    )