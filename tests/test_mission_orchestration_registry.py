import pytest

from forge.mission_orchestration.errors import (
    MissionStageConflictError,
    MissionStageNotFoundError,
)
from forge.mission_orchestration.models import StageDefinition, StageType
from forge.mission_orchestration.registry import MissionStageRegistry


def test_builtin_registry_contains_all_stages() -> None:
    registry = MissionStageRegistry.with_builtins()

    assert len(registry.list()) == 11
    assert registry.get("mission_validation").stage_type is StageType.MISSION_VALIDATION


def test_duplicate_stage_id_is_rejected() -> None:
    registry = MissionStageRegistry()
    definition = StageDefinition(
        stage_id="validate",
        stage_type=StageType.MISSION_VALIDATION,
        name="Validate",
    )
    registry.register(definition)

    with pytest.raises(MissionStageConflictError):
        registry.register(definition)


def test_missing_stage_is_rejected() -> None:
    with pytest.raises(MissionStageNotFoundError):
        MissionStageRegistry().get("missing")