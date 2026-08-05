"""Deterministic stage registry for M3.6 Mission Orchestration."""

from __future__ import annotations

from forge.mission_orchestration.errors import (
    MissionStageConflictError,
    MissionStageNotFoundError,
)
from forge.mission_orchestration.models import StageDefinition, StageType
from forge.mission_orchestration.stages import builtin_stage_definitions


class MissionStageRegistry:
    """Register and resolve orchestration stages deterministically."""

    def __init__(self) -> None:
        self._stages: dict[str, StageDefinition] = {}
        self._types: dict[StageType, str] = {}

    def register(self, definition: StageDefinition) -> None:
        """Register one unique stage definition."""
        if definition.stage_id in self._stages:
            raise MissionStageConflictError(
                f"stage already registered: {definition.stage_id}"
            )
        if definition.stage_type in self._types:
            raise MissionStageConflictError(
                f"stage type already registered: {definition.stage_type}"
            )
        self._stages[definition.stage_id] = definition
        self._types[definition.stage_type] = definition.stage_id

    def get(self, stage_id: str) -> StageDefinition:
        """Resolve a stage by identifier."""
        try:
            return self._stages[stage_id]
        except KeyError as exc:
            raise MissionStageNotFoundError(
                f"stage not registered: {stage_id}"
            ) from exc

    def get_by_type(self, stage_type: StageType) -> StageDefinition:
        """Resolve a stage by type."""
        try:
            return self.get(self._types[stage_type])
        except KeyError as exc:
            raise MissionStageNotFoundError(
                f"stage type not registered: {stage_type}"
            ) from exc

    def list(self) -> tuple[StageDefinition, ...]:
        """Return registered stages in deterministic order."""
        return tuple(
            self._stages[stage_id]
            for stage_id in sorted(self._stages)
        )

    @classmethod
    def with_builtins(cls) -> MissionStageRegistry:
        """Return a registry populated with all built-in stages."""
        registry = cls()
        for definition in builtin_stage_definitions():
            registry.register(definition)
        return registry