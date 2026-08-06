from forge.autonomous_planning.analysis import (
    PlanningAnalysis,
)
from forge.autonomous_planning.states import (
    PlanningIntent,
    PlanningRisk,
    StepKind,
)
from forge.autonomous_planning.step_synthesis import (
    synthesize_steps,
)


def analysis() -> PlanningAnalysis:
    return PlanningAnalysis(
        objective="Implement feature",
        target_paths=("forge/a.py",),
        required_capabilities=("editing",),
        constraints=(),
        acceptance_criteria=("Tests pass",),
        validation_commands=("python -m pytest",),
        architecture_constraints=(),
        evidence_references=(),
        estimated_risk=PlanningRisk.LOW,
        warnings=(),
    )


def test_feature_plan_contains_change_test_and_validation() -> None:
    steps = synthesize_steps(
        intent=PlanningIntent.IMPLEMENT_FEATURE,
        analysis=analysis(),
    )

    assert tuple(step.kind for step in steps) == (
        StepKind.ANALYSIS,
        StepKind.CODE_CHANGE,
        StepKind.TEST,
        StepKind.VALIDATION,
    )