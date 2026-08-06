from forge.autonomous_planning.analysis import (
    PlanningAnalysis,
)
from forge.autonomous_planning.dependency_synthesis import (
    synthesize_linear_dependencies,
)
from forge.autonomous_planning.states import (
    PlanningIntent,
    PlanningRisk,
)
from forge.autonomous_planning.step_synthesis import (
    synthesize_steps,
)


def test_dependencies_form_linear_chain() -> None:
    steps = synthesize_steps(
        intent=PlanningIntent.IMPLEMENT_FEATURE,
        analysis=PlanningAnalysis(
            objective="Implement feature",
            target_paths=(),
            required_capabilities=(),
            constraints=(),
            acceptance_criteria=(),
            validation_commands=(),
            architecture_constraints=(),
            evidence_references=(),
            estimated_risk=PlanningRisk.LOW,
            warnings=(),
        ),
    )

    dependencies = synthesize_linear_dependencies(steps)

    assert len(dependencies) == len(steps) - 1
    assert dependencies[0].source_step_id == (
        steps[1].step_id
    )
    assert dependencies[0].target_step_id == (
        steps[0].step_id
    )