from forge.autonomous_planning.eligibility import (
    eligible_step_ids,
    evaluate_step_eligibility,
)
from forge.autonomous_planning.graph import PlanningGraph
from forge.autonomous_planning.models import (
    PlanningDependency,
    PlanningStep,
)
from forge.autonomous_planning.states import (
    DependencyKind,
    StepKind,
)


def step(step_id: str, sequence: int) -> PlanningStep:
    return PlanningStep(
        step_id=step_id,
        sequence=sequence,
        name=step_id,
        description="Perform a repository-grounded action.",
        kind=StepKind.ANALYSIS,
    )


def test_eligibility_requires_completed_prerequisite() -> None:
    graph = PlanningGraph()
    graph.add_step(step("step-1", 1))
    graph.add_step(step("step-2", 2))
    graph.add_dependency(
        PlanningDependency(
            dependency_id="dependency-1",
            source_step_id="step-2",
            target_step_id="step-1",
            kind=DependencyKind.REQUIRES,
            rationale="Step two requires step one.",
        )
    )

    blocked = evaluate_step_eligibility(
        graph=graph,
        step_id="step-2",
        completed_step_ids=(),
    )
    ready = evaluate_step_eligibility(
        graph=graph,
        step_id="step-2",
        completed_step_ids=("step-1",),
    )

    assert not blocked.eligible
    assert ready.eligible
    assert eligible_step_ids(
        graph=graph,
        completed_step_ids=(),
    ) == ("step-1",)