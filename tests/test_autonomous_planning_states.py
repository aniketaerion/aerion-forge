from forge.autonomous_planning.states import (
    ApprovalRequirement,
    PlanningIntent,
    PlanningRisk,
    PlanningState,
    StepKind,
)


def test_state_values_are_stable() -> None:
    assert PlanningState.READY.value == "ready"
    assert PlanningIntent.FIX_DEFECT.value == "fix_defect"
    assert PlanningRisk.CRITICAL.value == "critical"
    assert StepKind.CODE_CHANGE.value == "code_change"
    assert ApprovalRequirement.PLAN.value == "plan"