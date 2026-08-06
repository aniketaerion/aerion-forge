"""Dependency graph for M5.7 autonomous execution."""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.autonomous_execution_v2.errors import (
    ExecutionContractError,
)
from forge.autonomous_execution_v2.models import (
    ExecutionDependency,
    ExecutionStep,
)


@dataclass(slots=True)
class ExecutionGraph:
    """Mutable deterministic execution graph."""

    _steps: dict[str, ExecutionStep] = field(
        default_factory=dict
    )
    _dependencies: dict[str, ExecutionDependency] = field(
        default_factory=dict
    )

    def add_step(self, step: ExecutionStep) -> None:
        existing = self._steps.get(step.step_id)

        if existing is not None and existing != step:
            raise ExecutionContractError(
                f"Conflicting execution step: {step.step_id}"
            )

        self._steps[step.step_id] = step

    def add_dependency(
        self,
        dependency: ExecutionDependency,
    ) -> None:
        if dependency.source_step_id not in self._steps:
            raise ExecutionContractError(
                "Dependency source step is unknown."
            )

        if dependency.target_step_id not in self._steps:
            raise ExecutionContractError(
                "Dependency target step is unknown."
            )

        existing = self._dependencies.get(
            dependency.dependency_id
        )

        if existing is not None and existing != dependency:
            raise ExecutionContractError(
                "Conflicting execution dependency: "
                f"{dependency.dependency_id}"
            )

        self._dependencies[
            dependency.dependency_id
        ] = dependency

    def steps(self) -> tuple[ExecutionStep, ...]:
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
    ) -> tuple[ExecutionDependency, ...]:
        return tuple(
            self._dependencies[key]
            for key in sorted(self._dependencies)
        )

    def prerequisite_ids(
        self,
        step_id: str,
    ) -> tuple[str, ...]:
        if step_id not in self._steps:
            raise ExecutionContractError(
                f"Unknown execution step: {step_id}"
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
            raise ExecutionContractError(
                f"Unknown execution step: {step_id}"
            )

        values = {
            dependency.source_step_id
            for dependency in self._dependencies.values()
            if dependency.target_step_id == step_id
        }
        return tuple(sorted(values))