"""Build-verification adapter for M3.8 Unified Agent Runtime."""

from __future__ import annotations

from forge.agent_runtime.adapters.base import (
    CallbackCapabilityAdapter,
    CapabilityExecutor,
)
from forge.agent_runtime.models import AgentCapability


class VerificationAdapter(CallbackCapabilityAdapter):
    """Bridge the unified runtime to build verification."""

    capability = AgentCapability.BUILD_VERIFICATION

    def __init__(self, executor: CapabilityExecutor) -> None:
        super().__init__(executor)