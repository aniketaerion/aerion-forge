"""Application service for autonomous planning."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_planning.approval import (
    PlanningApprovalDecision,
    approve_plan,
    reject_plan,
)
from forge.autonomous_planning.context import PlanningContext
from forge.autonomous_planning.models import (
    PlanningPlan,
    PlanningRequest,
    PlanningValidationResult,
)
from forge.autonomous_planning.plan_generation import (
    AutonomousPlanGenerator,
    GeneratedPlan,
)
from forge.autonomous_planning.repository import (
    InMemoryPlanningRepository,
)
from forge.autonomous_planning.validation import (
    AutonomousPlanValidator,
)


@dataclass(slots=True)
class AutonomousPlanningService:
    """Generate, validate, approve, and persist plans."""

    generator: AutonomousPlanGenerator
    validator: AutonomousPlanValidator
    repository: InMemoryPlanningRepository

    def create_plan(
        self,
        *,
        request: PlanningRequest,
        context: PlanningContext,
    ) -> tuple[GeneratedPlan, PlanningValidationResult]:
        self.repository.put_request(request)
        generated = self.generator.generate(
            request=request,
            context=context,
        )
        validation = self.validator.validate(
            generated.plan
        )

        if not validation.valid:
            failed = generated.plan.model_copy(
                update={"state": "failed"}
            )
            self.repository.put_plan(failed)
            generated = GeneratedPlan(
                analysis=generated.analysis,
                plan=failed,
                ordered_step_ids=generated.ordered_step_ids,
            )
        else:
            self.repository.put_plan(generated.plan)

        return generated, validation

    def approve(
        self,
        *,
        plan: PlanningPlan,
        decided_by: str,
        rationale: str,
    ) -> tuple[PlanningPlan, PlanningApprovalDecision]:
        approved, decision = approve_plan(
            plan=plan,
            decided_by=decided_by,
            rationale=rationale,
        )
        self.repository.put_plan(approved)
        return approved, decision

    def reject(
        self,
        *,
        plan: PlanningPlan,
        decided_by: str,
        rationale: str,
    ) -> tuple[PlanningPlan, PlanningApprovalDecision]:
        rejected, decision = reject_plan(
            plan=plan,
            decided_by=decided_by,
            rationale=rationale,
        )
        self.repository.put_plan(rejected)
        return rejected, decision