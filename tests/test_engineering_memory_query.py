"""Engineering Memory query tests."""

import pytest

from forge.engineering_memory.builder import EngineeringMemoryBuilder
from forge.engineering_memory.errors import (
    EngineeringMemoryNotFoundError,
)
from forge.engineering_memory.identifiers import (
    build_generation_id,
    build_memory_fingerprint,
    build_store_fingerprint,
)
from forge.engineering_memory.models import (
    EngineeringMemoryGeneration,
    EngineeringMemoryStore,
    MemoryRecord,
    MemoryType,
)
from forge.engineering_memory.query import (
    EngineeringMemoryQuery,
)
from tests.test_engineering_memory_builder import _inputs


def _records() -> tuple[MemoryRecord, ...]:
    mission, task_set, assessment = _inputs()

    return EngineeringMemoryBuilder().build(
        mission,
        task_set,
        assessment,
    )


def _store(
    *,
    include_history: bool = False,
) -> EngineeringMemoryStore:
    records = _records()
    active = {record.memory_id: record for record in records}
    fingerprint = build_store_fingerprint(active)

    generation = EngineeringMemoryGeneration(
        generation_id=build_generation_id(
            store_fingerprint=fingerprint,
        ),
        store_fingerprint=fingerprint,
        record_count=len(records),
        relationship_count=sum(len(record.relationships) for record in records),
        evidence_count=sum(len(record.evidence) for record in records),
    )

    history: dict[str, list[MemoryRecord]] = {}

    if include_history:
        original = records[0]
        draft = original.model_copy(
            update={
                "summary": original.summary + " Previous.",
                "memory_fingerprint": "0" * 64,
            }
        )
        previous = draft.model_copy(
            update={"memory_fingerprint": (build_memory_fingerprint(draft))}
        )
        history[original.memory_id] = [previous]

    return EngineeringMemoryStore(
        records=active,
        history=history,
        generation=generation,
    )


def _query(
    *,
    include_history: bool = False,
) -> EngineeringMemoryQuery:
    return EngineeringMemoryQuery(_store(include_history=include_history))


def test_get_returns_record() -> None:
    query = _query()
    expected = query.list_all()[0]

    actual = query.get(expected.memory_id)

    assert actual == expected


def test_get_returns_deep_copy() -> None:
    query = _query()
    first = query.list_all()[0]

    returned = query.get(first.memory_id)

    assert returned == first
    assert returned is not first


def test_get_rejects_unknown_memory_id() -> None:
    query = _query()

    with pytest.raises(EngineeringMemoryNotFoundError):
        query.get("memory-" + ("f" * 20))


def test_get_rejects_blank_memory_id() -> None:
    query = _query()

    with pytest.raises(EngineeringMemoryNotFoundError):
        query.get("   ")


def test_list_all_is_sorted() -> None:
    records = _query().list_all()

    assert tuple(record.memory_id for record in records) == tuple(
        sorted(record.memory_id for record in records)
    )


def test_by_mission_returns_all_lineage_records() -> None:
    mission, _, _ = _inputs()
    records = _query().by_mission(mission.mission_id)

    assert len(records) == 3
    assert all(mission.mission_id in record.mission_ids for record in records)


def test_by_unknown_mission_returns_empty_tuple() -> None:
    assert _query().by_mission("mission-unknown") == ()


def test_by_task_returns_task_and_decision_records() -> None:
    _, task_set, _ = _inputs()
    task_id = task_set.tasks[0].task_id

    records = _query().by_task(task_id)

    assert {record.memory_type for record in records} == {
        MemoryType.TASK,
        MemoryType.DECISION,
    }


def test_by_assessment_returns_decision_record() -> None:
    _, _, assessment = _inputs()

    records = _query().by_assessment(assessment.assessment_id)

    assert len(records) == 1
    assert records[0].memory_type is MemoryType.DECISION


def test_by_capability_filters_exactly() -> None:
    records = _query().by_capability("task-management")

    assert len(records) == 1
    assert records[0].memory_type is MemoryType.TASK


def test_by_milestone_filters_exactly() -> None:
    records = _query().by_milestone("2.3")

    assert len(records) == 1
    assert records[0].memory_type is MemoryType.DECISION


def test_by_type_filters_exactly() -> None:
    records = _query().by_type(MemoryType.MISSION)

    assert len(records) == 1
    assert records[0].memory_type is MemoryType.MISSION


def test_by_tag_normalizes_input() -> None:
    records = _query().by_tag(" Engineering Intelligence ")

    assert len(records) == 2
    assert {record.memory_type for record in records} == {
        MemoryType.MISSION,
        MemoryType.TASK,
    }


def test_related_to_returns_direct_relationships() -> None:
    query = _query()
    records = query.list_all()

    mission_record = next(record for record in records if record.memory_type is MemoryType.MISSION)
    task_record = next(record for record in records if record.memory_type is MemoryType.TASK)

    related = query.related_to(mission_record.memory_id)

    assert related == (task_record,)


def test_related_to_rejects_unknown_record() -> None:
    with pytest.raises(EngineeringMemoryNotFoundError):
        _query().related_to("memory-" + ("f" * 20))


def test_history_returns_previous_versions() -> None:
    query = _query(include_history=True)
    record = query.list_all()[0]

    history = query.history(record.memory_id)

    assert len(history) == 1
    assert history[0].memory_id == record.memory_id
    assert history[0].summary.endswith("Previous.")


def test_unknown_history_returns_empty_tuple() -> None:
    assert _query().history("memory-" + ("f" * 20)) == ()


def test_generation_returns_active_generation() -> None:
    generation = _query().generation()

    assert generation is not None
    assert generation.record_count == 3


def test_empty_store_has_no_generation() -> None:
    query = EngineeringMemoryQuery(EngineeringMemoryStore())

    assert query.generation() is None


def test_statistics_are_correct() -> None:
    statistics = _query().statistics()

    assert statistics == {
        "records": 3,
        "relationships": 2,
        "evidence": 3,
        "missions": 1,
        "tasks": len(_inputs()[1].tasks),
        "assessments": 1,
        "capabilities": 3,
        "permanent": 1,
    }


def test_query_does_not_mutate_original_store() -> None:
    store = _store()
    query = EngineeringMemoryQuery(store)

    query.list_all()
    query.statistics()

    assert query.generation() == store.generation
    assert len(store.records) == 3
