"""Convert an approved M5.6 plan into an M5.7 execution run."""

from __future__ import annotations

from forge.autonomous_execution_v2.identifiers import (
    execution_request_identifier,
    execution_run_identifier,
    execution_step_identifier,
)
from forge.autonomous_execution_v2.models import (
    ExecutionDependency,
    ExecutionRequest,
    ExecutionRun,
    ExecutionStep,
)
from forge.autonomous_planning.models import PlanningPlan
from forge.mission_runtime.context import MissionEngineeringContext
from forge.mission_runtime.models import MissionRequest


def execution_request_from_plan(
    *,
    request: MissionRequest,
    context: MissionEngineeringContext,
    plan: PlanningPlan,
    repository_fingerprint: str,
) -> ExecutionRequest:
    request_id = execution_request_identifier(
        {
            "mission_request_id": request.request_id,
            "plan_id": plan.plan_id,
            "plan_version": plan.version,
            "repository_root": context.workspace.repository_root,
            "repository_fingerprint": repository_fingerprint,
        }
    )

    return ExecutionRequest(
        request_id=request_id,
        plan_id=plan.plan_id,
        plan_version=plan.version,
        repository_root=context.workspace.repository_root,
        repository_fingerprint=repository_fingerprint,
        requested_by=request.requested_by,
    )


def execution_run_from_plan(
    *,
    execution_request: ExecutionRequest,
    plan: PlanningPlan,
) -> ExecutionRun:
    execution_steps: list[ExecutionStep] = []
    planning_to_execution: dict[str, str] = {}

    for planning_step in plan.steps:
        step_id = execution_step_identifier(
            {
                "execution_request_id": execution_request.request_id,
                "planning_step_id": planning_step.step_id,
                "sequence": planning_step.sequence,
            }
        )
        planning_to_execution[planning_step.step_id] = step_id

        execution_steps.append(
            ExecutionStep(
                step_id=step_id,
                planning_step_id=planning_step.step_id,
                sequence=planning_step.sequence,
                name=planning_step.name,
                description=planning_step.description,
                required_tools=planning_step.required_tools,
                expected_outputs=planning_step.expected_outputs,
                acceptance_criteria=planning_step.acceptance_criteria,
                risk=planning_step.risk.value,
                requires_approval=(
                    planning_step.approval_requirement.value != "none"
                ),
                destructive=planning_step.destructive,
            )
        )

    dependencies = tuple(
        ExecutionDependency(
            dependency_id=dependency.dependency_id,
            source_step_id=planning_to_execution[
                dependency.source_step_id
            ],
            target_step_id=planning_to_execution[
                dependency.target_step_id
            ],
            rationale=dependency.rationale,
        )
        for dependency in plan.dependencies
    )

    run_id = execution_run_identifier(
        {
            "execution_request_id": execution_request.request_id,
            "plan_id": plan.plan_id,
            "plan_version": plan.version,
            "steps": tuple(
                step.step_id
                for step in execution_steps
            ),
        }
    )

    return ExecutionRun(
        run_id=run_id,
        request_id=execution_request.request_id,
        plan_id=plan.plan_id,
        plan_version=plan.version,
        repository_root=execution_request.repository_root,
        repository_fingerprint=(
            execution_request.repository_fingerprint
        ),
        steps=tuple(execution_steps),
        dependencies=dependencies,
    )