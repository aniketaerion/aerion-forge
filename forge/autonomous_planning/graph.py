"""Directed acyclic planning graph."""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.autonomous_planning.errors import PlanningContractError
from forge.autonomous_planning.models import (
    PlanningDependency,
    PlanningStep,
)


@dataclass(slots=True)
class PlanningGraph:
    """Mutable builder for a deterministic planning DAG."""

    _steps: dict[str, PlanningStep] = field(default_factory=dict)
    _dependencies: dict[str, PlanningDependency] = field(
        default_factory=dict
    )

    def add_step(self, step: PlanningStep) -> None:
        existing = self._steps.get(step.step_id)

        if existing is not None and existing != step:
            raise PlanningContractError(
                f"Conflicting planning step: {step.step_id}"
            )

        self._steps[step.step_id] = step

    def add_dependency(
        self,
        dependency: PlanningDependency,
    ) -> None:
        if dependency.source_step_id not in self._steps:
            raise PlanningContractError(
                "Dependency source step is unknown."
            )

        if dependency.target_step_id not in self._steps:
            raise PlanningContractError(
                "Dependency target step is unknown."
            )

        existing = self._dependencies.get(
            dependency.dependency_id
        )

        if existing is not None and existing != dependency:
            raise PlanningContractError(
                "Conflicting planning dependency: "
                f"{dependency.dependency_id}"
            )

        self._dependencies[
            dependency.dependency_id
        ] = dependency

    def steps(self) -> tuple[PlanningStep, ...]:
        return tuple(
            sorted(
                self._steps.values(),
                key=lambda item: (
                    item.sequence,
                    item.step_id,
                ),
            )
        )

    def dependencies(
        self,
    ) -> tuple[PlanningDependency, ...]:
        return tuple(
            self._dependencies[key]
            for key in sorted(self._dependencies)
        )

    def prerequisite_ids(
        self,
        step_id: str,
    ) -> tuple[str, ...]:
        if step_id not in self._steps:
            raise PlanningContractError(
                f"Unknown planning step: {step_id}"
            )

        values = {
            dependency.target_step_id
            for dependency in self._dependencies.values()
            if dependency.source_step_id == step_id
        }
        return tuple(sorted(values))

    def dependent_ids(
        self,
        step_id: str,
    ) -> tuple[str, ...]:
        if step_id not in self._steps:
            raise PlanningContractError(
                f"Unknown planning step: {step_id}"
            )

        values = {
            dependency.source_step_id
            for dependency in self._dependencies.values()
            if dependency.target_step_id == step_id
        }
        return tuple(sorted(values))