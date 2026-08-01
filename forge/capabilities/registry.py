"""Deterministic registry construction, evaluation, and change detection."""

from forge.capabilities.errors import CapabilityValidationError
from forge.capabilities.identifiers import fingerprint
from forge.capabilities.models import (
    REGISTRY_ID,
    SCHEMA_VERSION,
    CapabilityChange,
    CapabilityChangeType,
    CapabilityDefinition,
    CapabilityEvaluation,
    CapabilityImplementationStatus,
    CapabilityLifecycle,
    CapabilityRegistry,
    CapabilityRegistryChangeSet,
    CapabilityRegistryConfiguration,
    CapabilityRegistryGeneration,
    CapabilityRegistryResult,
)
from forge.capabilities.validator import CapabilityRegistryValidator, registry_statistics


class CapabilityRegistryBuilder:
    def __init__(
        self,
        configuration: CapabilityRegistryConfiguration,
        validator: CapabilityRegistryValidator | None = None,
    ) -> None:
        self.configuration = configuration
        self.validator = validator or CapabilityRegistryValidator()

    def build(
        self,
        definitions: tuple[CapabilityDefinition, ...],
        previous: CapabilityRegistry | None = None,
    ) -> CapabilityRegistryResult:
        ordered = tuple(sorted(definitions, key=lambda x: x.capability_id))
        self.validator.require_definitions(ordered)
        known = {x.capability_id for x in ordered}
        unknown = sorted(set(self.configuration.disabled_ids) - known)
        if unknown and self.configuration.strict_validation:
            raise CapabilityValidationError(
                "unknown disabled capability IDs: " + ", ".join(unknown)
            )
        disabled = set(self.configuration.disabled_ids) & known
        states: dict[str, CapabilityEvaluation] = {}
        for _ in ordered:
            for definition in ordered:
                required = tuple(sorted(definition.required_capabilities))
                missing = tuple(x for x in required if x not in known)
                unavailable = tuple(x for x in required if x in states and not states[x].available)
                unresolved = tuple(x for x in required if x not in states)
                is_disabled = definition.capability_id in disabled
                implemented = (
                    definition.implementation_status is CapabilityImplementationStatus.IMPLEMENTED
                )
                available = (
                    implemented
                    and definition.lifecycle
                    not in (CapabilityLifecycle.PLANNED, CapabilityLifecycle.REMOVED)
                    and not is_disabled
                    and not missing
                    and not unavailable
                    and not unresolved
                )
                lifecycle = (
                    CapabilityLifecycle.DISABLED
                    if is_disabled
                    else (
                        CapabilityLifecycle.AVAILABLE
                        if available
                        and definition.lifecycle
                        not in (
                            CapabilityLifecycle.DEPRECATED,
                            CapabilityLifecycle.PARTIALLY_AVAILABLE,
                        )
                        else definition.lifecycle
                    )
                )
                messages = list(f"Unknown disabled capability ignored: {x}" for x in unknown)
                if not implemented:
                    messages.append("Capability has not been implemented.")
                if unavailable or unresolved:
                    messages.append("Required capability is unavailable.")
                states[definition.capability_id] = CapabilityEvaluation(
                    capability_id=definition.capability_id,
                    implementation_status=definition.implementation_status,
                    lifecycle=lifecycle,
                    available=available,
                    missing_required_capabilities=missing,
                    unavailable_required_capabilities=tuple(sorted((*unavailable, *unresolved))),
                    disabled=is_disabled,
                    validation_messages=tuple(sorted(messages)),
                    project_type_support=definition.supported_project_types,
                    configuration_status="disabled" if is_disabled else "enabled",
                )
        evaluations = tuple(states[x.capability_id] for x in ordered)
        if not self.configuration.include_planned:
            kept = {
                x.capability_id
                for x in ordered
                if states[x.capability_id].lifecycle is not CapabilityLifecycle.PLANNED
            }
            ordered = tuple(x for x in ordered if x.capability_id in kept)
            evaluations = tuple(x for x in evaluations if x.capability_id in kept)
        stats = registry_statistics(ordered, evaluations)
        portable = {
            "schema_version": SCHEMA_VERSION,
            "registry_id": REGISTRY_ID,
            "definitions": [x.model_dump(mode="json") for x in ordered],
            "evaluations": [
                x.model_dump(mode="json", exclude={"evaluated_registry_generation"})
                for x in evaluations
            ],
        }
        state = fingerprint(portable)
        generation_id = f"capabilities-{state[:20]}"
        evaluations = tuple(
            x.model_copy(update={"evaluated_registry_generation": generation_id})
            for x in evaluations
        )
        previous_id = (
            previous.generation.generation_id
            if previous and previous.generation.registry_fingerprint != state
            else (previous.generation.previous_generation_id if previous else None)
        )
        registry = CapabilityRegistry(
            definitions=ordered,
            evaluations=evaluations,
            statistics=stats,
            generation=CapabilityRegistryGeneration(
                generation_id=generation_id,
                registry_fingerprint=state,
                previous_generation_id=previous_id,
            ),
        )
        self.validator.require_registry(registry)
        return CapabilityRegistryResult(
            registry=registry, changes=diff_registries(previous, registry)
        )


def diff_registries(
    previous: CapabilityRegistry | None, current: CapabilityRegistry
) -> CapabilityRegistryChangeSet:
    old = {} if previous is None else {x.capability_id: x for x in previous.definitions}
    new = {x.capability_id: x for x in current.definitions}
    old_eval = {} if previous is None else {x.capability_id: x for x in previous.evaluations}
    new_eval = {x.capability_id: x for x in current.evaluations}
    groups: dict[str, list[CapabilityChange]] = {
        x: [] for x in ("added", "modified", "removed", "unchanged")
    }
    for capability_id in sorted(set(old) | set(new)):
        if capability_id not in old:
            group = "added"
            change = CapabilityChangeType.ADDED
        elif capability_id not in new:
            group = "removed"
            change = CapabilityChangeType.REMOVED
        elif old[capability_id] != new[capability_id] or old_eval[capability_id].model_dump(
            exclude={"evaluated_registry_generation"}
        ) != new_eval[capability_id].model_dump(exclude={"evaluated_registry_generation"}):
            group = "modified"
            change = CapabilityChangeType.MODIFIED
        else:
            group = "unchanged"
            change = CapabilityChangeType.UNCHANGED
        groups[group].append(CapabilityChange(capability_id=capability_id, change_type=change))
    return CapabilityRegistryChangeSet(**{k: tuple(v) for k, v in groups.items()})
