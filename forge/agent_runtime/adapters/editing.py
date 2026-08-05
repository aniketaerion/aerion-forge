"""Safe-code-editing adapter for M3.8 Unified Agent Runtime."""

from __future__ import annotations

from forge.agent_runtime.adapters.base import (
    CallbackCapabilityAdapter,
    CapabilityExecutor,
)
from forge.agent_runtime.models import AgentCapability


class EditingAdapter(CallbackCapabilityAdapter):
    """Bridge the unified runtime to safe code editing."""

    capability = AgentCapability.SAFE_CODE_EDITING

    def __init__(self, executor: CapabilityExecutor) -> None:
        super().__init__(executor)