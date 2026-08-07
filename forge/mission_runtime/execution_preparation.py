"""Prepare an approved mission plan for M5.7 execution."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_execution_v2.authority import ExecutionAuthority
from forge.autonomous_execution_v2.models import (
    ExecutionRequest,
    ExecutionRun,
)
from forge.autonomous_planning.models import PlanningPlan
from forge.mission_runtime.approval import (
    MissionApprovalRequirement,
    assert_plan_approved,
)
from forge.mission_runtime.context import MissionEngineeringContext
from forge.mission_runtime.execution_authority import (
    execution_authority_for_plan,
)
from forge.mission_runtime.execution_conversion import (
    execution_request_from_plan,
    execution_run_from_plan,
)
from forge.mission_runtime.models import (
    MissionApproval,
    MissionRequest,
)


@dataclass(frozen=True, slots=True)
class MissionExecutionPreparation:
    execution_request: ExecutionRequest
    run: ExecutionRun
    authority: ExecutionAuthority


def prepare_execution(
    *,
    request: MissionRequest,
    context: MissionEngineeringContext,
    plan: PlanningPlan,
    approval_requirement: MissionApprovalRequirement,
    approval: MissionApproval | None,
    repository_fingerprint: str,
) -> MissionExecutionPreparation:
    assert_plan_approved(
        requirement=approval_requirement,
        approval=approval,
    )

    execution_request = execution_request_from_plan(
        request=request,
        context=context,
        plan=plan,
        repository_fingerprint=repository_fingerprint,
    )

    run = execution_run_from_plan(
        execution_request=execution_request,
        plan=plan,
    )

    authority = execution_authority_for_plan(
        request=request,
        context=context,
        plan=plan,
        approval=approval,
    )

    return MissionExecutionPreparation(
        execution_request=execution_request,
        run=run,
        authority=authority,
    )