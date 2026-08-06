"""Deterministic dependency synthesis for planning steps."""

from __future__ import annotations

from itertools import pairwise

from forge.autonomous_planning.identifiers import (
    planning_dependency_identifier,
)
from forge.autonomous_planning.models import (
    PlanningDependency,
    PlanningStep,
)
from forge.autonomous_planning.states import DependencyKind


def synthesize_linear_dependencies(
    steps: tuple[PlanningStep, ...],
) -> tuple[PlanningDependency, ...]:
    """Create strict prerequisite dependencies by sequence."""
    ordered = tuple(
        sorted(
            steps,
            key=lambda item: (
                item.sequence,
                item.step_id,
            ),
        )
    )
    dependencies: list[PlanningDependency] = []

    for previous, current in pairwise(ordered):
        payload = {
            "source": current.step_id,
            "target": previous.step_id,
            "kind": DependencyKind.REQUIRES.value,
        }
        dependencies.append(
            PlanningDependency(
                dependency_id=planning_dependency_identifier(
                    payload
                ),
                source_step_id=current.step_id,
                target_step_id=previous.step_id,
                kind=DependencyKind.REQUIRES,
                rationale=(
                    f"{current.name} requires completion of "
                    f"{previous.name}."
                ),
            )
        )

    return tuple(dependencies)