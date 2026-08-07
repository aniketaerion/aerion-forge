"""Mission planning orchestration for M5.8 Package 2."""

from __future__ import annotations

from dataclasses import dataclass

from forge.mission_runtime.approval import (
    MissionApprovalRequirement,
    plan_approval_requirement,
)
from forge.mission_runtime.context import MissionEngineeringContext
from forge.mission_runtime.memory_integration import (
    MissionMemoryContext,
    MissionMemoryIntegration,
)
from forge.mission_runtime.models import MissionRequest
from forge.mission_runtime.planning_integration import (
    MissionPlanningIntegration,
    MissionPlanningResult,
)
from forge.mission_runtime.policies import MissionRuntimePolicy


@dataclass(frozen=True, slots=True)
class MissionPlanPreparation:
    memory: MissionMemoryContext
    planning: MissionPlanningResult
    approval: MissionApprovalRequirement


@dataclass(slots=True)
class MissionPlanningOrchestrator:
    """Connect mission context, M5.5 memory, and M5.6 planning."""

    memory: MissionMemoryIntegration
    planning: MissionPlanningIntegration
    policy: MissionRuntimePolicy

    def prepare(
        self,
        *,
        request: MissionRequest,
        context: MissionEngineeringContext,
    ) -> MissionPlanPreparation:
        memory_context = self.memory.retrieve(
            request=request,
            context=context,
        )
        planning_result = self.planning.create_plan(
            request=request,
            context=context,
            memory=memory_context,
        )
        approval = plan_approval_requirement(
            plan=planning_result.plan,
            policy=self.policy,
        )

        return MissionPlanPreparation(
            memory=memory_context,
            planning=planning_result,
            approval=approval,
        )