"""Executable plan projection for M5.2."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_execution.dependency_graph import (
    validate_dependency_graph,
)
from forge.autonomous_execution.scheduler import ordered_steps
from forge.autonomous_runtime.models import MissionPlan, MissionStep


@dataclass(frozen=True, slots=True)
class ExecutablePlan:
    """Validated deterministic projection of a mission plan."""

    plan_id: str
    mission_id: str
    version: int
    steps: tuple[MissionStep, ...]
    total_steps: int


def build_executable_plan(
    plan: MissionPlan,
) -> ExecutablePlan:
    """Validate and project a mission plan for execution."""
    validate_dependency_graph(plan.steps)
    steps = ordered_steps(plan)

    return ExecutablePlan(
        plan_id=plan.plan_id,
        mission_id=plan.mission_id,
        version=plan.version,
        steps=steps,
        total_steps=len(steps),
    )