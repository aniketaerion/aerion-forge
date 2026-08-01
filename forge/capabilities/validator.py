"""Definition, dependency, and complete-registry validation."""

from collections import Counter

from forge.capabilities.errors import CapabilityCycleError, CapabilityValidationError
from forge.capabilities.identifiers import fingerprint
from forge.capabilities.models import (
    REGISTRY_ID,
    SCHEMA_VERSION,
    CapabilityAccessMode,
    CapabilityApprovalPolicy,
    CapabilityDefinition,
    CapabilityImplementationStatus,
    CapabilityLifecycle,
    CapabilityRegistry,
    CapabilityRegistryStatistics,
    RegistryValidationResult,
)


class CapabilityRegistryValidator:
    def validate_definitions(
        self, definitions: tuple[CapabilityDefinition, ...]
    ) -> RegistryValidationResult:
        messages: list[str] = []
        ids = [item.capability_id for item in definitions]
        if len(ids) != len(set(ids)):
            messages.append("duplicate capability ID")
        known = set(ids)
        definitions_by_id = {item.capability_id: item for item in definitions}
        replacements: dict[str, str] = {}
        for item in definitions:
            for dependency in (*item.required_capabilities, *item.optional_capabilities):
                if dependency not in known:
                    messages.append(f"{item.capability_id}: unknown dependency {dependency}")
                if dependency == item.capability_id:
                    messages.append(f"{item.capability_id}: self-dependency")
                target = definitions_by_id.get(dependency)
                if target is not None and target.lifecycle is CapabilityLifecycle.REMOVED:
                    messages.append(f"{item.capability_id}: dependency {dependency} is removed")
            if (
                item.access_mode is CapabilityAccessMode.TARGET_MUTATING
                and item.approval_policy is CapabilityApprovalPolicy.NONE
            ):
                messages.append(f"{item.capability_id}: target mutation requires approval")
            if (
                item.implementation_status is CapabilityImplementationStatus.NOT_IMPLEMENTED
                and item.lifecycle is not CapabilityLifecycle.PLANNED
            ):
                messages.append(f"{item.capability_id}: unimplemented capability must be planned")
            if (
                item.lifecycle is CapabilityLifecycle.REMOVED
                and item.implementation_status is CapabilityImplementationStatus.IMPLEMENTED
            ):
                messages.append(f"{item.capability_id}: removed capability cannot be implemented")
            if item.deprecation and item.deprecation.replacement_capability_id:
                replacement = item.deprecation.replacement_capability_id
                if replacement not in known:
                    messages.append(f"{item.capability_id}: unknown replacement {replacement}")
                elif replacement == item.capability_id:
                    messages.append(f"{item.capability_id}: self replacement")
                replacements[item.capability_id] = replacement
        for start in sorted(replacements):
            visited: set[str] = set()
            current = start
            while current in replacements:
                if current in visited:
                    messages.append(f"replacement cycle involving {start}")
                    break
                visited.add(current)
                current = replacements[current]
        if not messages:
            try:
                self._cycles(definitions)
            except CapabilityCycleError as exc:
                messages.append(str(exc))
        return RegistryValidationResult(valid=not messages, messages=tuple(sorted(messages)))

    @staticmethod
    def _cycles(definitions: tuple[CapabilityDefinition, ...]) -> None:
        graph = {item.capability_id: item.required_capabilities for item in definitions}
        active: set[str] = set()
        complete: set[str] = set()

        def visit(node: str, path: tuple[str, ...]) -> None:
            if node in active:
                raise CapabilityCycleError("dependency cycle: " + " -> ".join((*path, node)))
            if node in complete:
                return
            active.add(node)
            for child in sorted(graph.get(node, ())):
                if child in graph:
                    visit(child, (*path, node))
            active.remove(node)
            complete.add(node)

        for node in sorted(graph):
            visit(node, ())

    def require_definitions(self, definitions: tuple[CapabilityDefinition, ...]) -> None:
        result = self.validate_definitions(definitions)
        if not result.valid:
            raise CapabilityValidationError("; ".join(result.messages))

    def require_registry(self, registry: CapabilityRegistry) -> None:
        self.require_definitions(registry.definitions)
        if registry.schema_version != SCHEMA_VERSION or registry.registry_id != REGISTRY_ID:
            raise CapabilityValidationError("registry identity or schema mismatch")
        evaluations = {item.capability_id: item for item in registry.evaluations}
        for item in registry.evaluations:
            if item.available and any(
                not evaluations[dep].available
                for dep in next(
                    d for d in registry.definitions if d.capability_id == item.capability_id
                ).required_capabilities
            ):
                raise CapabilityValidationError(
                    f"{item.capability_id}: unavailable required dependency"
                )
        expected = registry_statistics(registry.definitions, registry.evaluations)
        if expected != registry.statistics:
            raise CapabilityValidationError("registry statistics are inconsistent")
        portable = {
            "schema_version": registry.schema_version,
            "registry_id": registry.registry_id,
            "definitions": [x.model_dump(mode="json") for x in registry.definitions],
            "evaluations": [
                x.model_dump(mode="json", exclude={"evaluated_registry_generation"})
                for x in registry.evaluations
            ],
        }
        if fingerprint(portable) != registry.generation.registry_fingerprint:
            raise CapabilityValidationError("registry fingerprint is inconsistent")


def registry_statistics(
    definitions: tuple[CapabilityDefinition, ...], evaluations: tuple[object, ...]
) -> CapabilityRegistryStatistics:
    from forge.capabilities.models import CapabilityEvaluation

    typed = tuple(item for item in evaluations if isinstance(item, CapabilityEvaluation))

    def counts(values: list[str]) -> dict[str, int]:
        return dict(sorted(Counter(values).items()))

    return CapabilityRegistryStatistics(
        total_capabilities=len(definitions),
        available_capabilities=sum(x.available for x in typed),
        planned_capabilities=sum(x.lifecycle is CapabilityLifecycle.PLANNED for x in typed),
        implemented_capabilities=sum(
            x.implementation_status is CapabilityImplementationStatus.IMPLEMENTED for x in typed
        ),
        partially_available_capabilities=sum(
            x.lifecycle is CapabilityLifecycle.PARTIALLY_AVAILABLE for x in typed
        ),
        disabled_capabilities=sum(x.disabled for x in typed),
        deprecated_capabilities=sum(x.lifecycle is CapabilityLifecycle.DEPRECATED for x in typed),
        removed_capabilities=sum(x.lifecycle is CapabilityLifecycle.REMOVED for x in typed),
        read_only_capabilities=sum(
            x.access_mode is CapabilityAccessMode.READ_ONLY for x in definitions
        ),
        forge_internal_write_capabilities=sum(
            x.access_mode is CapabilityAccessMode.FORGE_INTERNAL_WRITE for x in definitions
        ),
        target_mutating_capabilities=sum(
            x.access_mode is CapabilityAccessMode.TARGET_MUTATING for x in definitions
        ),
        external_side_effect_capabilities=sum(
            x.access_mode is CapabilityAccessMode.EXTERNAL_SIDE_EFFECT for x in definitions
        ),
        capabilities_by_category=counts([x.category.value for x in definitions]),
        capabilities_by_maturity=counts([x.maturity.value for x in definitions]),
        capabilities_by_phase=counts([x.phase for x in definitions]),
        capabilities_by_milestone=counts([x.milestone for x in definitions]),
    )
