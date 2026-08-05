"""Mission-planning adapter for M3.8 Unified Agent Runtime."""

from __future__ import annotations

from forge.agent_runtime.adapters.base import (
    CallbackCapabilityAdapter,
    CapabilityExecutor,
)
from forge.agent_runtime.models import AgentCapability


class PlanningAdapter(CallbackCapabilityAdapter):
    """Bridge the unified runtime to mission planning."""

    capability = AgentCapability.MISSION_PLANNING

    def __init__(self, executor: CapabilityExecutor) -> None:
        super().__init__(executor)