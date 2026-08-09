"""Planning orchestration for M5.9 Package 3."""

from __future__ import annotations

from dataclasses import dataclass

from forge.general_engineering.change_planner import build_change_plan
from forge.general_engineering.models import (
    ChangePlan,
    ChangeSpecification,
    EngineeringContext,
    EngineeringRequest,
)
from forge.general_engineering.plan_validator import validate_change_plan


@dataclass(frozen=True)
class EngineeringPlanningResult:
    plan: ChangePlan
    planned_file_count: int
    evidence_count: int


class EngineeringChangePlanningService:
    """Produce and validate a repository-grounded change plan."""

    def plan(
        self,
        *,
        request: EngineeringRequest,
        specification: ChangeSpecification,
        context: EngineeringContext,
    ) -> EngineeringPlanningResult:
        plan = build_change_plan(
            request=request,
            specification=specification,
            context=context,
        )
        validate_change_plan(
            request=request,
            specification=specification,
            context=context,
            plan=plan,
        )
        return EngineeringPlanningResult(
            plan=plan,
            planned_file_count=len(plan.file_changes),
            evidence_count=len(plan.evidence_ids),
        )


engineering_change_planning_service = EngineeringChangePlanningService()