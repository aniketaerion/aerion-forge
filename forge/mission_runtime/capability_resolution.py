"""Repository-grounded capability selection for M5.8."""

from __future__ import annotations

from dataclasses import dataclass

from forge.capabilities import CapabilityRegistryQuery
from forge.capabilities.models import CapabilityDefinition
from forge.mission_runtime.context import (
    MissionCapabilitySelection,
    MissionTechnologyContext,
)


def _normalized_signals(
    technology: MissionTechnologyContext,
) -> set[str]:
    values = {
        technology.project_type.value,
        *technology.technologies,
    }

    for value in (
        technology.primary_language,
        technology.framework,
        technology.database,
        technology.package_manager,
        technology.build_system,
        technology.test_framework,
    ):
        if value:
            values.add(value)

    return {
        value.strip().casefold()
        for value in values
        if value.strip()
    }


def _capability_matches(
    definition: CapabilityDefinition,
    signals: set[str],
) -> bool:
    project_types = {
        value.strip().casefold()
        for value in definition.supported_project_types
    }

    tags = {
        value.strip().casefold()
        for value in definition.tags
    }

    return bool(
        project_types.intersection(signals)
        or tags.intersection(signals)
    )


@dataclass(frozen=True, slots=True)
class MissionCapabilityResolver:
    """Select only registered capabilities supported by repository evidence."""

    query: CapabilityRegistryQuery

    def resolve(
        self,
        technology: MissionTechnologyContext,
    ) -> MissionCapabilitySelection:
        signals = _normalized_signals(technology)
        available = {
            definition.capability_id: definition
            for definition in self.query.list_available_capabilities()
        }
        selected = tuple(
            sorted(
                definition.capability_id
                for definition in available.values()
                if _capability_matches(
                    definition,
                    signals,
                )
            )
        )

        rationale = tuple(
            f"{capability_id}: matched repository technology/project evidence."
            for capability_id in selected
        )

        return MissionCapabilitySelection(
            capability_ids=selected,
            unavailable_capability_ids=(),
            rationale=rationale,
            repository_grounded=True,
        )