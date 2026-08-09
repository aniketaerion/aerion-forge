"""Production Agent Runtime registry for bounded M5.8 execution."""

from __future__ import annotations

from forge.agent_runtime.adapters.change_planning import ChangePlanningAdapter
from forge.agent_runtime.adapters.editing import EditingAdapter
from forge.agent_runtime.adapters.impact import ImpactAdapter
from forge.agent_runtime.adapters.planning import PlanningAdapter
from forge.agent_runtime.adapters.verification import VerificationAdapter
from forge.agent_runtime.models import AgentCapability, AgentRuntimePolicy
from forge.agent_runtime.production_executors import (
    change_planning_executor,
    editing_executor,
    impact_executor,
    planning_executor,
    verification_executor,
)
from forge.agent_runtime.registry import AgentCapabilityRegistry
from forge.agent_runtime.service import AgentRuntimeService

PRODUCTION_CAPABILITIES = (
    AgentCapability.MISSION_PLANNING,
    AgentCapability.IMPACT_ANALYSIS,
    AgentCapability.SAFE_CHANGE_PLANNING,
    AgentCapability.SAFE_CODE_EDITING,
    AgentCapability.BUILD_VERIFICATION,
)


def production_agent_service() -> AgentRuntimeService:
    registry = AgentCapabilityRegistry(
        (
            PlanningAdapter(planning_executor),
            ImpactAdapter(impact_executor),
            ChangePlanningAdapter(change_planning_executor),
            EditingAdapter(editing_executor),
            VerificationAdapter(verification_executor),
        )
    )
    policy = AgentRuntimePolicy(
        allowed_capabilities=PRODUCTION_CAPABILITIES,
        allow_code_changes=True,
        allow_network=False,
        allow_self_modification=False,
        require_clean_working_tree=True,
        require_plan_approval=True,
        require_edit_approval=True,
        require_release_approval=True,
    )
    return AgentRuntimeService(registry, policy)