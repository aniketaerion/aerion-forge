"""Task report renderer tests."""

import json
from pathlib import Path

import pytest

from forge.tasks.errors import TaskReportError
from forge.tasks.identifiers import (
    build_task_fingerprint,
    build_task_id,
    build_task_set_fingerprint,
)
from forge.tasks.models import (
    EngineeringTask,
    TaskAcceptanceCriterion,
    TaskChange,
    TaskChangeSet,
    TaskChangeType,
    TaskGeneration,
    TaskSet,
    TaskValidationCategory,
    TaskValidationRequirement,
)
from forge.tasks.renderer import TaskRenderer
from forge.tasks.validator import calculate_statistics


def _task() -> EngineeringTask:
    task_id = build_task_id(
        mission_id="mission-1",
        workstream_id="workstream-1",
        parent_task_id=None,
        title="Implement Procurement",
        sequence=1,
    )

    task = EngineeringTask(
        task_id=task_id,
        task_fingerprint="0" * 64,
        mission_id="mission-1",
        workstream_id="workstream-1",
        title="Implement Procurement",
        description="Implement the approved procurement contract.",
        acceptance_criteria=(
            TaskAcceptanceCriterion(
                criterion_id="criterion-1",
                statement="Procurement behavior is verified.",
            ),
        ),
        validation_requirements=(
            TaskValidationRequirement(
                requirement_id="validation-1",
                category=TaskValidationCategory.UNIT_TESTING,
                description="Unit tests pass.",
            ),
        ),
        sequence=1,
    )

    return task.model_copy(
        update={
            "task_fingerprint": build_task_fingerprint(task),
        }
    )


def _task_set() -> TaskSet:
    tasks = (_task(),)

    task_set = TaskSet(
        mission_id="mission-1",
        mission_fingerprint="a" * 64,
        task_set_fingerprint="0" * 64,
        tasks=tasks,
        statistics=calculate_statistics(tasks),
        source_fingerprints={
            "mission": "a" * 64,
        },
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


def _changes(task_set: TaskSet) -> TaskChangeSet:
    return TaskChangeSet(
        mission_id=task_set.mission_id,
        changes=(
            TaskChange(
                task_id=task_set.tasks[0].task_id,
                field="task",
                change_type=TaskChangeType.CREATED,
            ),
        ),
    )


def test_render_returns_complete_report_suite() -> None:
    task_set = _task_set()
    reports = TaskRenderer().render(
        task_set,
        _generation(task_set),
        _changes(task_set),
    )

    assert tuple(reports) == TaskRenderer.REPORT_NAMES


def test_json_reports_are_valid_and_deterministic() -> None:
    task_set = _task_set()
    renderer = TaskRenderer()

    first = renderer.render(
        task_set,
        _generation(task_set),
        _changes(task_set),
    )
    second = renderer.render(
        task_set,
        _generation(task_set),
        _changes(task_set),
    )

    assert first == second

    for name in (
        "TASK_PLAN.json",
        "TASK_SUMMARY.json",
        "TASK_CHANGES.json",
    ):
        assert json.loads(first[name])


def test_markdown_contains_task_contract() -> None:
    task_set = _task_set()
    reports = TaskRenderer().render(
        task_set,
        _generation(task_set),
        _changes(task_set),
    )

    plan = reports["TASK_PLAN.md"]

    assert "# Task Management Plan" in plan
    assert "Implement Procurement" in plan
    assert "Procurement behavior is verified." in plan
    assert "Unit tests pass." in plan


def test_write_creates_canonical_reports(
    tmp_path: Path,
) -> None:
    task_set = _task_set()
    renderer = TaskRenderer()
    reports = renderer.render(
        task_set,
        _generation(task_set),
        _changes(task_set),
    )

    paths = renderer.write(tmp_path, reports)

    assert paths == TaskRenderer.REPORT_NAMES
    assert sorted(path.name for path in tmp_path.iterdir()) == sorted(
        TaskRenderer.REPORT_NAMES
    )


def test_write_rejects_incomplete_report_set(
    tmp_path: Path,
) -> None:
    with pytest.raises(TaskReportError):
        TaskRenderer().write(
            tmp_path,
            {
                "TASK_PLAN.json": "{}\n",
            },
        )


def test_written_reports_are_repeatable(
    tmp_path: Path,
) -> None:
    task_set = _task_set()
    renderer = TaskRenderer()
    reports = renderer.render(
        task_set,
        _generation(task_set),
        _changes(task_set),
    )

    renderer.write(tmp_path, reports)

    first = {
        path.name: path.read_bytes()
        for path in tmp_path.iterdir()
    }

    renderer.write(tmp_path, reports)

    second = {
        path.name: path.read_bytes()
        for path in tmp_path.iterdir()
    }

    assert first == second
