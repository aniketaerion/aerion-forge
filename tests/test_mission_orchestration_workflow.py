import pytest

from forge.mission_orchestration.errors import MissionDependencyError
from forge.mission_orchestration.models import (
    MissionRequest,
    StageDefinition,
    StageType,
)
from forge.mission_orchestration.workflow import (
    build_default_workflow,
    topological_order,
)


def request() -> MissionRequest:
    return MissionRequest(
        mission_id="mission-1",
        repository_root=".",
        objective="Build feature",
        requested_paths=("forge/app.py",),
    )


def test_default_workflow_is_deterministic() -> None:
    first = build_default_workflow(request())
    second = build_default_workflow(request())

    assert first.workflow_id == second.workflow_id
    assert first.stages[0].stage_id == "mission_validation"
    assert first.stages[-1].stage_id == "mission_reporting"


def test_topological_order_respects_dependencies() -> None:
    stages = (
        StageDefinition(
            stage_id="b",
            stage_type=StageType.SAFE_CHANGE_PLAN,
            name="B",
            dependencies=("a",),
        ),
        StageDefinition(
            stage_id="a",
            stage_type=StageType.MISSION_VALIDATION,
            name="A",
        ),
    )

    ordered = topological_order(stages)

    assert tuple(stage.stage_id for stage in ordered) == ("a", "b")


def test_cycle_is_rejected() -> None:
    stages = (
        StageDefinition(
            stage_id="a",
            stage_type=StageType.MISSION_VALIDATION,
            name="A",
            dependencies=("b",),
        ),
        StageDefinition(
            stage_id="b",
            stage_type=StageType.SAFE_CHANGE_PLAN,
            name="B",
            dependencies=("a",),
        ),
    )

    with pytest.raises(MissionDependencyError):
        topological_order(stages)