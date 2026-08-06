"""Autonomous plan generation service."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_planning.analysis import (
    PlanningAnalysis,
    analyse_planning_request,
)
from forge.autonomous_planning.context import PlanningContext
from forge.autonomous_planning.dependency_synthesis import (
    synthesize_linear_dependencies,
)
from forge.autonomous_planning.graph_builder import (
    PlanningGraphBuilder,
)
from forge.autonomous_planning.identifiers import (
    planning_plan_identifier,
)
from forge.autonomous_planning.models import (
    PlanningPlan,
    PlanningRequest,
)
from forge.autonomous_planning.policies import (
    AutonomousPlanningPolicy,
)
from forge.autonomous_planning.states import (
    PlanningRisk,
    PlanningState,
)
from forge.autonomous_planning.step_synthesis import (
    synthesize_steps,
)


@dataclass(frozen=True, slots=True)
class GeneratedPlan:
    """Generated plan and the analysis that produced it."""

    analysis: PlanningAnalysis
    plan: PlanningPlan
    ordered_step_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AutonomousPlanGenerator:
    """Generate deterministic, repository-grounded plans."""

    policy: AutonomousPlanningPolicy

    def generate(
        self,
        *,
        request: PlanningRequest,
        context: PlanningContext,
    ) -> GeneratedPlan:
        analysis = analyse_planning_request(
            request=request,
            context=context,
        )
        steps = synthesize_steps(
            intent=request.intent,
            analysis=analysis,
        )
        dependencies = synthesize_linear_dependencies(
            steps
        )
        requires_approval = any(
            step.approval_requirement.value != "none"
            for step in steps
        )
        risk = max(
            (step.risk for step in steps),
            key=lambda item: (
                PlanningRisk.LOW,
                PlanningRisk.MEDIUM,
                PlanningRisk.HIGH,
                PlanningRisk.CRITICAL,
            ).index(item),
        )
        payload = {
            "request_id": request.request_id,
            "objective": analysis.objective,
            "steps": tuple(
                step.step_id
                for step in steps
            ),
            "dependencies": tuple(
                dependency.dependency_id
                for dependency in dependencies
            ),
        }
        state = (
            PlanningState.AWAITING_APPROVAL
            if requires_approval
            else PlanningState.READY
        )
        plan = PlanningPlan(
            plan_id=planning_plan_identifier(payload),
            request_id=request.request_id,
            state=state,
            summary=(
                "Repository-grounded autonomous plan for: "
                f"{analysis.objective}"
            ),
            steps=steps,
            dependencies=dependencies,
            risk=risk,
            requires_approval=requires_approval,
            warnings=analysis.warnings,
        )
        graph_result = PlanningGraphBuilder(
            policy=self.policy
        ).build(plan)

        return GeneratedPlan(
            analysis=analysis,
            plan=plan,
            ordered_step_ids=graph_result.ordered_step_ids,
        )