"""Task-store persistence tests."""

import json
from pathlib import Path

import pytest

from forge.tasks.errors import (
    TaskSchemaMismatchError,
    TaskStoreCorruptionError,
)
from forge.tasks.identifiers import (
    build_task_fingerprint,
    build_task_id,
    build_task_set_fingerprint,
)
from forge.tasks.models import (
    EngineeringTask,
    TaskAcceptanceCriterion,
    TaskGeneration,
    TaskSet,
    TaskStatus,
    TaskValidationCategory,
    TaskValidationRequirement,
)
from forge.tasks.store import TaskRepository
from forge.tasks.validator import calculate_statistics


def _task(
    title: str,
    sequence: int,
    status: TaskStatus = TaskStatus.DRAFT,
) -> EngineeringTask:
    task_id = build_task_id(
        mission_id="mission-1",
        workstream_id="workstream-1",
        parent_task_id=None,
        title=title,
        sequence=sequence,
    )

    task = EngineeringTask(
        task_id=task_id,
        task_fingerprint="0" * 64,
        mission_id="mission-1",
        workstream_id="workstream-1",
        title=title,
        description=f"Complete {title}.",
        status=status,
        acceptance_criteria=(
            TaskAcceptanceCriterion(
                criterion_id=f"criterion-{sequence}",
                statement="Required behavior is verified.",
            ),
        ),
        validation_requirements=(
            TaskValidationRequirement(
                requirement_id=f"validation-{sequence}",
                category=TaskValidationCategory.UNIT_TESTING,
                description="Unit tests pass.",
            ),
        ),
        sequence=sequence,
    )

    return task.model_copy(
        update={
            "task_fingerprint": build_task_fingerprint(task),
        }
    )


def _task_set(
    tasks: tuple[EngineeringTask, ...],
) -> TaskSet:
    task_set = TaskSet(
        mission_id="mission-1",
        mission_fingerprint="a" * 64,
        task_set_fingerprint="0" * 64,
        tasks=tasks,
        statistics=calculate_statistics(tasks),
        source_fingerprints={"mission": "a" * 64},
    )

    return task_set.model_copy(
        update={
            "task_set_fingerprint":
                build_task_set_fingerprint(task_set),
        }
    )


def _generation(task_set: TaskSet) -> TaskGeneration:
    return TaskGeneration(
        generation_id=(
            f"task-generation-{task_set.task_set_fingerprint[:20]}"
        ),
        mission_id=task_set.mission_id,
        mission_fingerprint=task_set.mission_fingerprint,
        task_set_fingerprint=task_set.task_set_fingerprint,
        task_count=len(task_set.tasks),
        statistics=task_set.statistics,
    )


def test_missing_store_returns_empty_store(
    tmp_path: Path,
) -> None:
    repository = TaskRepository(tmp_path / "tasks.json")

    store = repository.load()

    assert store.tasks == {}
    assert store.history == {}
    assert store.generations == {}


def test_save_and_load_task_set(
    tmp_path: Path,
) -> None:
    repository = TaskRepository(tmp_path / "tasks.json")
    task_set = _task_set((_task("Task One", 1),))

    saved = repository.save(
        task_set,
        _generation(task_set),
    )
    loaded = repository.load()

    assert saved == loaded
    assert tuple(loaded.tasks) == (
        task_set.tasks[0].task_id,
    )
    assert loaded.generations["mission-1"].task_count == 1


def test_repeated_identical_save_does_not_add_history(
    tmp_path: Path,
) -> None:
    repository = TaskRepository(tmp_path / "tasks.json")
    task_set = _task_set((_task("Task One", 1),))
    generation = _generation(task_set)

    repository.save(task_set, generation)
    repository.save(task_set, generation)

    assert repository.load().history == {}


def test_changed_task_adds_bounded_history(
    tmp_path: Path,
) -> None:
    repository = TaskRepository(
        tmp_path / "tasks.json",
        history_limit=1,
    )

    first_task = _task("Task One", 1)
    first_set = _task_set((first_task,))
    repository.save(first_set, _generation(first_set))

    changed = first_task.model_copy(
        update={
            "status": TaskStatus.READY,
            "task_fingerprint": "0" * 64,
        }
    )
    changed = changed.model_copy(
        update={
            "task_fingerprint":
                build_task_fingerprint(changed),
        }
    )
    second_set = _task_set((changed,))
    repository.save(second_set, _generation(second_set))

    history = repository.load().history[first_task.task_id]

    assert len(history) == 1
    assert history[0].status is TaskStatus.DRAFT


def test_snapshot_and_restore(
    tmp_path: Path,
) -> None:
    path = tmp_path / "tasks.json"
    repository = TaskRepository(path)

    first_set = _task_set((_task("Task One", 1),))
    repository.save(first_set, _generation(first_set))
    snapshot = repository.snapshot_bytes()

    second_set = _task_set((_task("Task Two", 2),))
    repository.save(second_set, _generation(second_set))

    repository.restore_bytes(snapshot)

    assert repository.load().tasks == {
        first_set.tasks[0].task_id: first_set.tasks[0],
    }


def test_restore_none_removes_store(
    tmp_path: Path,
) -> None:
    path = tmp_path / "tasks.json"
    repository = TaskRepository(path)
    task_set = _task_set((_task("Task One", 1),))

    repository.save(task_set, _generation(task_set))
    repository.restore_bytes(None)

    assert not path.exists()


def test_corrupt_store_is_rejected(
    tmp_path: Path,
) -> None:
    path = tmp_path / "tasks.json"
    path.write_text("{invalid", encoding="utf-8")

    with pytest.raises(TaskStoreCorruptionError):
        TaskRepository(path).load()


def test_schema_mismatch_is_rejected(
    tmp_path: Path,
) -> None:
    path = tmp_path / "tasks.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "99.0",
                "tasks": {},
                "history": {},
                "generations": {},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(TaskSchemaMismatchError):
        TaskRepository(path).load()


def test_write_probe_leaves_no_files(
    tmp_path: Path,
) -> None:
    repository = TaskRepository(tmp_path / "tasks.json")

    repository.probe_write()

    assert list(tmp_path.iterdir()) == []


def test_serialized_store_is_deterministic(
    tmp_path: Path,
) -> None:
    path = tmp_path / "tasks.json"
    repository = TaskRepository(path)
    task_set = _task_set(
        (
            _task("Task One", 1),
            _task("Task Two", 2),
        )
    )
    generation = _generation(task_set)

    repository.save(task_set, generation)
    first = path.read_bytes()

    repository.save(task_set, generation)
    second = path.read_bytes()

    assert first == second
