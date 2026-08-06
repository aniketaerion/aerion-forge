"""Dependency graph evaluation for executable mission steps."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_execution.errors import ExecutionContractError
from forge.autonomous_runtime.models import MissionStep


@dataclass(frozen=True, slots=True)
class DependencyEvaluation:
    """Dependency evaluation for one step."""

    satisfied: bool
    missing_dependencies: tuple[str, ...]


def evaluate_dependencies(
    step: MissionStep,
    *,
    completed_step_ids: frozenset[str],
) -> DependencyEvaluation:
    """Check whether all dependencies for a step are complete."""
    missing = tuple(
        dependency
        for dependency in step.depends_on
        if dependency not in completed_step_ids
    )
    return DependencyEvaluation(
        satisfied=not missing,
        missing_dependencies=missing,
    )


def assert_dependencies_satisfied(
    step: MissionStep,
    *,
    completed_step_ids: frozenset[str],
) -> None:
    """Raise when step dependencies are incomplete."""
    result = evaluate_dependencies(
        step,
        completed_step_ids=completed_step_ids,
    )
    if not result.satisfied:
        raise ExecutionContractError(
            "Step dependencies are incomplete: "
            + ", ".join(result.missing_dependencies)
        )


def validate_dependency_graph(
    steps: tuple[MissionStep, ...],
) -> None:
    """Reject unknown dependencies, self-dependencies, and cycles."""
    step_ids = {step.step_id for step in steps}

    for step in steps:
        unknown = set(step.depends_on).difference(step_ids)
        if unknown:
            raise ExecutionContractError(
                f"Step {step.step_id} has unknown dependencies: "
                + ", ".join(sorted(unknown))
            )
        if step.step_id in step.depends_on:
            raise ExecutionContractError(
                f"Step {step.step_id} cannot depend on itself."
            )

    dependencies = {
        step.step_id: set(step.depends_on)
        for step in steps
    }
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(step_id: str) -> None:
        if step_id in visited:
            return
        if step_id in visiting:
            raise ExecutionContractError(
                "Execution plan contains a dependency cycle."
            )

        visiting.add(step_id)
        for dependency in dependencies[step_id]:
            visit(dependency)
        visiting.remove(step_id)
        visited.add(step_id)

    for step_id in sorted(step_ids):
        visit(step_id)