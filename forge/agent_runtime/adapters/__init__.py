"""M3.8 unified-runtime capability adapters."""

from forge.agent_runtime.adapters.base import (
    AgentCapabilityAdapter,
    CallbackCapabilityAdapter,
    CapabilityExecutor,
    failed_result,
    succeeded_result,
)
from forge.agent_runtime.adapters.change_planning import (
    ChangePlanningAdapter,
)
from forge.agent_runtime.adapters.editing import EditingAdapter
from forge.agent_runtime.adapters.impact import ImpactAdapter
from forge.agent_runtime.adapters.planning import PlanningAdapter
from forge.agent_runtime.adapters.repair import RepairAdapter
from forge.agent_runtime.adapters.verification import VerificationAdapter

__all__ = [
    "AgentCapabilityAdapter",
    "CallbackCapabilityAdapter",
    "CapabilityExecutor",
    "ChangePlanningAdapter",
    "EditingAdapter",
    "ImpactAdapter",
    "PlanningAdapter",
    "RepairAdapter",
    "VerificationAdapter",
    "failed_result",
    "succeeded_result",
]