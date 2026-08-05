"""Workflow graph construction and validation for M3.6."""

from __future__ import annotations

from collections import defaultdict, deque

from forge.mission_orchestration.errors import MissionDependencyError
from forge.mission_orchestration.identifiers import workflow_identifier
from forge.mission_orchestration.models import (
    MissionRequest,
    MissionWorkflow,
    StageDefinition,
)
from forge.mission_orchestration.policies import MissionOrchestrationPolicy
from forge.mission_orchestration.registry import MissionStageRegistry


def topological_order(
    stages: tuple[StageDefinition, ...],
) -> tuple[StageDefinition, ...]:
    """Return deterministic topological order or reject cycles."""
    by_id = {stage.stage_id: stage for stage in stages}
    indegree = {stage.stage_id: 0 for stage in stages}
    dependants: dict[str, list[str]] = defaultdict(list)

    for stage in stages:
        for dependency in stage.dependencies:
            if dependency not in by_id:
                raise MissionDependencyError(
                    f"unknown dependency {dependency} for {stage.stage_id}"
                )
            indegree[stage.stage_id] += 1
            dependants[dependency].append(stage.stage_id)

    ready = deque(sorted(
        stage_id
        for stage_id, count in indegree.items()
        if count == 0
    ))
    ordered: list[StageDefinition] = []

    while ready:
        stage_id = ready.popleft()
        ordered.append(by_id[stage_id])
        for dependant in sorted(dependants[stage_id]):
            indegree[dependant] -= 1
            if indegree[dependant] == 0:
                ready.append(dependant)

    if len(ordered) != len(stages):
        raise MissionDependencyError("workflow contains a dependency cycle")

    return tuple(ordered)


def validate_required_stages(
    stages: tuple[StageDefinition, ...],
    policy: MissionOrchestrationPolicy,
) -> None:
    """Ensure all policy-required stages are present."""
    present = {stage.stage_type for stage in stages}
    missing = [
        stage_type.value
        for stage_type in policy.required_stages
        if stage_type not in present
    ]
    if missing:
        raise MissionDependencyError(
            f"workflow is missing required stages: {', '.join(sorted(missing))}"
        )


def build_default_workflow(
    request: MissionRequest,
    *,
    registry: MissionStageRegistry | None = None,
    policy: MissionOrchestrationPolicy | None = None,
) -> MissionWorkflow:
    """Build the default deterministic workflow for one mission."""
    active_registry = registry or MissionStageRegistry.with_builtins()
    active_policy = policy or MissionOrchestrationPolicy()

    stages = active_registry.list()
    validate_required_stages(stages, active_policy)
    ordered = topological_order(stages)

    workflow_id = workflow_identifier(
        {
            "mission_id": request.mission_id,
            "stages": [
                {
                    "stage_id": stage.stage_id,
                    "stage_type": stage.stage_type.value,
                    "dependencies": stage.dependencies,
                    "approval_required": stage.approval_required,
                    "optional": stage.optional,
                    "max_attempts": stage.max_attempts,
                }
                for stage in ordered
            ],
        }
    )
    return MissionWorkflow(
        workflow_id=workflow_id,
        mission_id=request.mission_id,
        stages=ordered,
    )