"""Deterministic autonomous-repair provider registry."""

from __future__ import annotations

from forge.autonomous_repair.errors import (
    RepairProviderConflictError,
    RepairProviderNotFoundError,
)
from forge.autonomous_repair.models import RepairProviderType
from forge.autonomous_repair.providers import (
    AutonomousRepairProvider,
    ExactPatchProvider,
    RuffFixProvider,
)


class RepairProviderRegistry:
    """Register and resolve bounded repair providers."""

    def __init__(self) -> None:
        self._providers: dict[RepairProviderType, AutonomousRepairProvider] = {}

    def register(self, provider: AutonomousRepairProvider) -> None:
        if provider.provider_type in self._providers:
            raise RepairProviderConflictError(
                f"provider already registered: {provider.provider_type}"
            )
        self._providers[provider.provider_type] = provider

    def get(self, provider_type: RepairProviderType) -> AutonomousRepairProvider:
        try:
            return self._providers[provider_type]
        except KeyError as exc:
            raise RepairProviderNotFoundError(
                f"provider not registered: {provider_type}"
            ) from exc

    def list_provider_types(self) -> tuple[RepairProviderType, ...]:
        return tuple(sorted(self._providers, key=lambda item: item.value))

    @classmethod
    def with_builtins(cls) -> RepairProviderRegistry:
        registry = cls()
        registry.register(ExactPatchProvider())
        registry.register(RuffFixProvider())
        return registry