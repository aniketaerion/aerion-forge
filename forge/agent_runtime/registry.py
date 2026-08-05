"""Capability-adapter registry for M3.8 Unified Agent Runtime."""

from __future__ import annotations

from collections.abc import Iterable

from forge.agent_runtime.adapters import AgentCapabilityAdapter
from forge.agent_runtime.errors import AgentRuntimeCapabilityError
from forge.agent_runtime.models import AgentCapability


class AgentCapabilityRegistry:
    """Deterministic registry of unified-runtime capability adapters."""

    def __init__(
        self,
        adapters: Iterable[AgentCapabilityAdapter] = (),
    ) -> None:
        self._adapters: dict[
            AgentCapability,
            AgentCapabilityAdapter,
        ] = {}

        for adapter in adapters:
            self.register(adapter)

    def register(
        self,
        adapter: AgentCapabilityAdapter,
    ) -> None:
        """Register one adapter and reject duplicate capabilities."""
        if adapter.capability in self._adapters:
            raise AgentRuntimeCapabilityError(
                "duplicate capability adapter registration: "
                f"{adapter.capability.value}"
            )

        self._adapters[adapter.capability] = adapter

    def get(
        self,
        capability: AgentCapability,
    ) -> AgentCapabilityAdapter:
        """Return the adapter registered for a capability."""
        try:
            return self._adapters[capability]
        except KeyError as exc:
            raise AgentRuntimeCapabilityError(
                f"capability adapter is not registered: {capability.value}"
            ) from exc

    def contains(
        self,
        capability: AgentCapability,
    ) -> bool:
        """Return whether the capability is registered."""
        return capability in self._adapters

    def capabilities(self) -> tuple[AgentCapability, ...]:
        """Return registered capabilities in deterministic order."""
        return tuple(
            sorted(
                self._adapters,
                key=lambda capability: capability.value,
            )
        )

    def validate_required(
        self,
        capabilities: Iterable[AgentCapability],
    ) -> None:
        """Fail when any required capability lacks an adapter."""
        missing = tuple(
            sorted(
                {
                    capability
                    for capability in capabilities
                    if capability not in self._adapters
                },
                key=lambda capability: capability.value,
            )
        )

        if missing:
            names = ", ".join(
                capability.value for capability in missing
            )
            raise AgentRuntimeCapabilityError(
                f"required capability adapters are missing: {names}"
            )