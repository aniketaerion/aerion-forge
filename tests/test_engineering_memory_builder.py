"""Engineering Memory builder tests."""

import pytest

from forge.engineering_memory.builder import EngineeringMemoryBuilder
from forge.engineering_memory.errors import (
    EngineeringMemoryValidationError,
)
from forge.engineering_memory.models import (
    MemoryRetentionPolicy,
    MemoryType,
)
from forge.impact.builder import ImpactAssessmentBuilder
from forge.impact.models import ImpactAssessment
from forge.planning.models import MissionPlan, MissionWorkstream
from forge.tasks.decomposer import decompose_mission
from forge.tasks.models import TaskSet
from tests.test_task_decomposition import _mission


def _inputs() -> tuple[MissionPlan, TaskSet, ImpactAssessment]:
    mission = _mission(
        workstreams=(
            MissionWorkstream(
                workstream_id="engineering-memory",
                name="Engineering Memory",
                objective="Persist engineering knowledge.",
                expected_outputs=("Engineering Memory",),
            ),
        ),
    )

    task_set = decompose_mission(mission)

    assessment = ImpactAssessmentBuilder().build(
        mission,
        task_set,
    )

    return mission, task_set, assessment


def test_builder_creates_three_records() -> None:
    mission, task_set, assessment = _inputs()

    records = EngineeringMemoryBuilder().build(
        mission,
        task_set,
        assessment,
    )

    assert len(records) == 3


def test_builder_creates_expected_memory_types() -> None:
    mission, task_set, assessment = _inputs()

    records = EngineeringMemoryBuilder().build(
        mission,
        task_set,
        assessment,
    )

    assert {record.memory_type for record in records} == {
        MemoryType.MISSION,
        MemoryType.TASK,
        MemoryType.DECISION,
    }


def test_builder_output_is_deterministic() -> None:
    mission, task_set, assessment = _inputs()
    builder = EngineeringMemoryBuilder()

    first = builder.build(
        mission,
        task_set,
        assessment,
    )
    second = builder.build(
        mission,
        task_set,
        assessment,
    )

    assert first == second


def test_builder_output_is_sorted_by_memory_id() -> None:
    mission, task_set, assessment = _inputs()

    records = EngineeringMemoryBuilder().build(
        mission,
        task_set,
        assessment,
    )

    assert tuple(record.memory_id for record in records) == tuple(
        sorted(record.memory_id for record in records)
    )


def test_mission_record_contains_mission_lineage() -> None:
    mission, task_set, assessment = _inputs()

    records = EngineeringMemoryBuilder().build(
        mission,
        task_set,
        assessment,
    )

    record = next(item for item in records if item.memory_type is MemoryType.MISSION)

    assert record.mission_ids == (mission.mission_id,)
    assert record.capability_ids == ("mission-planning",)
    assert record.milestones == ("2.1",)


def test_task_record_contains_all_task_ids() -> None:
    mission, task_set, assessment = _inputs()

    records = EngineeringMemoryBuilder().build(
        mission,
        task_set,
        assessment,
    )

    record = next(item for item in records if item.memory_type is MemoryType.TASK)

    assert record.task_ids == tuple(sorted(task.task_id for task in task_set.tasks))
    assert record.capability_ids == ("task-management",)


def test_decision_record_contains_assessment_lineage() -> None:
    mission, task_set, assessment = _inputs()

    records = EngineeringMemoryBuilder().build(
        mission,
        task_set,
        assessment,
    )

    record = next(item for item in records if item.memory_type is MemoryType.DECISION)

    assert record.assessment_ids == (assessment.assessment_id,)
    assert record.capability_ids == ("impact-decision-engine",)


def test_decision_record_is_permanent() -> None:
    mission, task_set, assessment = _inputs()

    records = EngineeringMemoryBuilder().build(
        mission,
        task_set,
        assessment,
    )

    record = next(item for item in records if item.memory_type is MemoryType.DECISION)

    assert record.retention_policy is MemoryRetentionPolicy.PERMANENT


def test_task_record_references_mission_record() -> None:
    mission, task_set, assessment = _inputs()

    records = EngineeringMemoryBuilder().build(
        mission,
        task_set,
        assessment,
    )

    mission_record = next(item for item in records if item.memory_type is MemoryType.MISSION)
    task_record = next(item for item in records if item.memory_type is MemoryType.TASK)

    assert len(task_record.relationships) == 1
    assert task_record.relationships[0].target_memory_id == mission_record.memory_id


def test_decision_record_references_task_record() -> None:
    mission, task_set, assessment = _inputs()

    records = EngineeringMemoryBuilder().build(
        mission,
        task_set,
        assessment,
    )

    task_record = next(item for item in records if item.memory_type is MemoryType.TASK)
    decision_record = next(item for item in records if item.memory_type is MemoryType.DECISION)

    assert len(decision_record.relationships) == 1
    assert decision_record.relationships[0].target_memory_id == task_record.memory_id


def test_builder_rejects_mission_id_mismatch() -> None:
    mission, task_set, assessment = _inputs()

    invalid = task_set.model_copy(update={"mission_id": "mission-other"})

    with pytest.raises(EngineeringMemoryValidationError):
        EngineeringMemoryBuilder().build(
            mission,
            invalid,
            assessment,
        )


def test_builder_rejects_mission_fingerprint_mismatch() -> None:
    mission, task_set, assessment = _inputs()

    invalid = task_set.model_copy(update={"mission_fingerprint": "f" * 64})

    with pytest.raises(EngineeringMemoryValidationError):
        EngineeringMemoryBuilder().build(
            mission,
            invalid,
            assessment,
        )


def test_builder_rejects_assessment_mission_mismatch() -> None:
    mission, task_set, assessment = _inputs()

    invalid = assessment.model_copy(update={"mission_id": "mission-other"})

    with pytest.raises(EngineeringMemoryValidationError):
        EngineeringMemoryBuilder().build(
            mission,
            task_set,
            invalid,
        )


def test_builder_rejects_task_set_fingerprint_mismatch() -> None:
    mission, task_set, assessment = _inputs()

    invalid = assessment.model_copy(update={"task_set_fingerprint": "e" * 64})

    with pytest.raises(EngineeringMemoryValidationError):
        EngineeringMemoryBuilder().build(
            mission,
            task_set,
            invalid,
        )


def test_builder_rejects_task_id_mismatch() -> None:
    mission, task_set, assessment = _inputs()

    invalid = assessment.model_copy(update={"task_ids": ("task-invalid",)})

    with pytest.raises(EngineeringMemoryValidationError):
        EngineeringMemoryBuilder().build(
            mission,
            task_set,
            invalid,
        )


def test_builder_rejects_empty_task_set() -> None:
    mission, task_set, assessment = _inputs()

    invalid = task_set.model_copy(update={"tasks": ()})

    with pytest.raises(EngineeringMemoryValidationError):
        EngineeringMemoryBuilder().build(
            mission,
            invalid,
            assessment,
        )
