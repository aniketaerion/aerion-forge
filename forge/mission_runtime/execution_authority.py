"""Translate mission approval into M5.7 execution authority."""

from __future__ import annotations

from forge.autonomous_execution_v2.authority import ExecutionAuthority
from forge.autonomous_planning.models import PlanningPlan
from forge.mission_runtime.context import MissionEngineeringContext
from forge.mission_runtime.models import (
    MissionApproval,
    MissionRequest,
)
from forge.mission_runtime.states import MissionApprovalDecision


def execution_authority_for_plan(
    *,
    request: MissionRequest,
    context: MissionEngineeringContext,
    plan: PlanningPlan,
    approval: MissionApproval | None,
) -> ExecutionAuthority:
    approved = (
        approval is not None
        and approval.decision
        is MissionApprovalDecision.APPROVED
    )

    tools = tuple(
        sorted(
            {
                tool
                for step in plan.steps
                for tool in step.required_tools
            }
        )
    )

    return ExecutionAuthority(
        subject=request.requested_by,
        repository_root=context.workspace.repository_root,
        permitted_tools=tools,
        permitted_capabilities=(
            context.capabilities.capability_ids
        ),
        high_risk_approved=approved,
        destructive_approved=approved,
    )