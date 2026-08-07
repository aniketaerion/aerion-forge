"""M5.6 planning integration for mission runtime."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_planning.context import PlanningContext
from forge.autonomous_planning.identifiers import (
    planning_request_identifier,
)
from forge.autonomous_planning.models import (
    PlanningPlan,
    PlanningRequest,
    PlanningValidationResult,
)
from forge.autonomous_planning.service import AutonomousPlanningService
from forge.autonomous_planning.states import PlanningIntent
from forge.mission_runtime.context import MissionEngineeringContext
from forge.mission_runtime.memory_integration import MissionMemoryContext
from forge.mission_runtime.models import MissionRequest


@dataclass(frozen=True, slots=True)
class MissionPlanningResult:
    planning_request: PlanningRequest
    plan: PlanningPlan
    validation: PlanningValidationResult
    memory_query_id: str


@dataclass(slots=True)
class MissionPlanningIntegration:
    """Translate a mission into the existing M5.6 planner."""

    service: AutonomousPlanningService

    def create_plan(
        self,
        *,
        request: MissionRequest,
        context: MissionEngineeringContext,
        memory: MissionMemoryContext,
    ) -> MissionPlanningResult:
        planning_request_id = planning_request_identifier(
            {
                "mission_request_id": request.request_id,
                "repository_root": context.workspace.repository_root,
                "objective": request.statement,
                "capabilities": context.capabilities.capability_ids,
            }
        )

        planning_request = PlanningRequest(
            request_id=planning_request_id,
            objective=request.statement,
            repository_root=context.workspace.repository_root,
            intent=PlanningIntent.IMPLEMENT_FEATURE,
            requested_capabilities=(
                context.capabilities.capability_ids
            ),
            created_by=request.requested_by,
        )

        planning_context = PlanningContext(
            repository_root=context.workspace.repository_root,
            repository_fingerprint="mission-runtime-context",
            known_capabilities=context.capabilities.capability_ids,
            architecture_constraints=(),
            operational_constraints=(),
            evidence_references=(
                *context.context_references,
                *memory.evidence_references,
            ),
        )

        generated, validation = self.service.create_plan(
            request=planning_request,
            context=planning_context,
        )

        return MissionPlanningResult(
            planning_request=planning_request,
            plan=generated.plan,
            validation=validation,
            memory_query_id=memory.query_id,
        )