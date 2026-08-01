"""Typed, read-only capability registry queries."""

from forge.capabilities.errors import CapabilityNotFoundError
from forge.capabilities.models import (
    CapabilityCategory,
    CapabilityCommand,
    CapabilityDefinition,
    CapabilityOutput,
    CapabilityRegistry,
    CapabilityRegistryStatistics,
)


class CapabilityRegistryQuery:
    def __init__(self, registry: CapabilityRegistry) -> None:
        self.registry = registry
        self._definitions = {x.capability_id: x for x in registry.definitions}
        self._evaluations = {x.capability_id: x for x in registry.evaluations}
        dependents: dict[str, list[CapabilityDefinition]] = {
            capability_id: [] for capability_id in self._definitions
        }
        for definition in registry.definitions:
            dependencies = (*definition.required_capabilities, *definition.optional_capabilities)
            for dependency in dependencies:
                if dependency in dependents:
                    dependents[dependency].append(definition)
        self._dependents = {
            key: tuple(sorted(values, key=lambda item: item.capability_id))
            for key, values in dependents.items()
        }

    def get_capability(self, capability_id: str) -> CapabilityDefinition:
        try:
            return self._definitions[capability_id]
        except KeyError as exc:
            raise CapabilityNotFoundError(f"Unknown capability: {capability_id}") from exc

    def list_capabilities(self) -> tuple[CapabilityDefinition, ...]:
        return self.registry.definitions

    def list_available_capabilities(self) -> tuple[CapabilityDefinition, ...]:
        return tuple(
            x for x in self.registry.definitions if self._evaluations[x.capability_id].available
        )

    def list_planned_capabilities(self) -> tuple[CapabilityDefinition, ...]:
        return tuple(
            x
            for x in self.registry.definitions
            if self._evaluations[x.capability_id].lifecycle.value == "planned"
        )

    def get_capabilities_by_category(
        self, category: CapabilityCategory
    ) -> tuple[CapabilityDefinition, ...]:
        return tuple(x for x in self.registry.definitions if x.category is category)

    def get_capabilities_for_project_type(
        self, project_type: str
    ) -> tuple[CapabilityDefinition, ...]:
        return tuple(
            x for x in self.registry.definitions if project_type in x.supported_project_types
        )

    def get_required_capabilities(self, capability_id: str) -> tuple[CapabilityDefinition, ...]:
        return tuple(
            self.get_capability(x) for x in self.get_capability(capability_id).required_capabilities
        )

    def get_optional_capabilities(self, capability_id: str) -> tuple[CapabilityDefinition, ...]:
        return tuple(
            self.get_capability(x) for x in self.get_capability(capability_id).optional_capabilities
        )

    def get_dependents(self, capability_id: str) -> tuple[CapabilityDefinition, ...]:
        self.get_capability(capability_id)
        return self._dependents[capability_id]

    def is_available(self, capability_id: str) -> bool:
        self.get_capability(capability_id)
        return self._evaluations[capability_id].available

    def get_missing_requirements(self, capability_id: str) -> tuple[str, ...]:
        self.get_capability(capability_id)
        e = self._evaluations[capability_id]
        return tuple(
            sorted((*e.missing_required_capabilities, *e.unavailable_required_capabilities))
        )

    def get_capability_outputs(self, capability_id: str) -> tuple[CapabilityOutput, ...]:
        return self.get_capability(capability_id).produced_outputs

    def get_capability_commands(self, capability_id: str) -> tuple[CapabilityCommand, ...]:
        return self.get_capability(capability_id).cli_commands

    def get_registry_summary(self) -> CapabilityRegistryStatistics:
        return self.registry.statistics
