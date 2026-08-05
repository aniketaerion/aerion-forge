"""Autonomous-repair adapter for M3.8 Unified Agent Runtime."""

from __future__ import annotations

from forge.agent_runtime.adapters.base import (
    CallbackCapabilityAdapter,
    CapabilityExecutor,
)
from forge.agent_runtime.models import AgentCapability


class RepairAdapter(CallbackCapabilityAdapter):
    """Bridge the unified runtime to autonomous repair."""

    capability = AgentCapability.AUTONOMOUS_REPAIR

    def __init__(self, executor: CapabilityExecutor) -> None:
        super().__init__(executor)