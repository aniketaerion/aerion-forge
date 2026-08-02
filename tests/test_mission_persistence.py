"""Persistence, report, rollback, and determinism tests."""

import hashlib
from pathlib import Path

import pytest

from forge.planning.models import MissionPlanningConfiguration
from forge.planning.renderer import MissionRenderer
from forge.planning.service import MissionPlanningService


def _prepare(root: Path) -> tuple[Path, Path]:
    memory = root / "memory"
    reports = root / "reports" / "latest"

    memory.mkdir(parents=True)
    reports.mkdir(parents=True)

    (memory / "workspaces.json").write_text(
        '{"workspaces": {}}\n',
        encoding="utf-8",
    )

    return memory, reports


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_persisted_plan_writes_store_and_reports(
    tmp_path: Path,
) -> None:
    memory, reports = _prepare(tmp_path)

    service = MissionPlanningService(
        memory_path=memory,
        reports_path=reports,
        configuration=MissionPlanningConfiguration(),
    )

    result = service.plan(
        "Document the current architecture",
        target=str(tmp_path),
        persist=True,
        cwd=tmp_path,
    )

    assert (memory / "missions.json").exists()
    assert result.report_paths

    expected = {
        "MISSION_PLAN.json",
        "MISSION_SUMMARY.json",
        "MISSION_CONTEXT.json",
        "MISSION_RISKS.json",
        "MISSION_ASSUMPTIONS.json",
        "MISSION_QUESTIONS.json",
        "MISSION_CHANGES.json",
        "MISSION_PLAN.md",
        "MISSION_SUMMARY.md",
    }

    assert expected == {
        path.name
        for path in reports.glob("MISSION_*")
    }


def test_repeated_persistence_is_deterministic(
    tmp_path: Path,
) -> None:
    memory, reports = _prepare(tmp_path)

    service = MissionPlanningService(
        memory_path=memory,
        reports_path=reports,
    )

    first = service.plan(
        "Document the current architecture",
        target=str(tmp_path),
        persist=True,
        cwd=tmp_path,
    )

    second = service.plan(
        "Document the current architecture",
        target=str(tmp_path),
        persist=True,
        cwd=tmp_path,
    )

    second_hashes = {
        path.name: _sha256(path)
        for path in reports.glob("MISSION_*")
    }

    third = service.plan(
        "Document the current architecture",
        target=str(tmp_path),
        persist=True,
        cwd=tmp_path,
    )

    third_hashes = {
        path.name: _sha256(path)
        for path in reports.glob("MISSION_*")
    }

    assert (
        first.changes.changes[0].change_type.value
        == "created"
    )
    assert (
        second.changes.changes[0].change_type.value
        == "unchanged"
    )
    assert (
        third.changes.changes[0].change_type.value
        == "unchanged"
    )

    assert (
        first.plan.mission_id
        == second.plan.mission_id
        == third.plan.mission_id
    )
    assert (
        first.plan.mission_fingerprint
        == second.plan.mission_fingerprint
        == third.plan.mission_fingerprint
    )
    assert (
        first.generation.generation_id
        == second.generation.generation_id
        == third.generation.generation_id
    )

    assert second_hashes == third_hashes


def test_no_persist_writes_nothing(
    tmp_path: Path,
) -> None:
    memory, reports = _prepare(tmp_path)

    service = MissionPlanningService(
        memory_path=memory,
        reports_path=reports,
    )

    service.plan(
        "Document the current architecture",
        target=str(tmp_path),
        persist=False,
        cwd=tmp_path,
    )

    assert not (memory / "missions.json").exists()
    assert not tuple(reports.glob("MISSION_*"))


class FailingRenderer(MissionRenderer):
    def write(
        self,
        directory: Path,
        reports: dict[str, str],
    ) -> tuple[str, ...]:
        raise OSError("simulated renderer failure")


def test_renderer_failure_restores_previous_store(
    tmp_path: Path,
) -> None:
    memory, reports = _prepare(tmp_path)

    service = MissionPlanningService(
        memory_path=memory,
        reports_path=reports,
    )

    service.plan(
        "Document the current architecture",
        target=str(tmp_path),
        persist=True,
        cwd=tmp_path,
    )

    store_path = memory / "missions.json"
    original_store = store_path.read_bytes()

    failing = MissionPlanningService(
        memory_path=memory,
        reports_path=reports,
        renderer=FailingRenderer(),
    )

    with pytest.raises(OSError):
        failing.plan(
            "Migrate the database schema",
            target=str(tmp_path),
            persist=True,
            cwd=tmp_path,
        )

    assert store_path.read_bytes() == original_store


def test_store_history_is_bounded(
    tmp_path: Path,
) -> None:
    memory, reports = _prepare(tmp_path)

    service = MissionPlanningService(
        memory_path=memory,
        reports_path=reports,
        configuration=MissionPlanningConfiguration(
            history_limit=1,
        ),
    )

    service.plan(
        "Document the current architecture",
        target=str(tmp_path),
        persist=True,
        cwd=tmp_path,
    )

    service.plan(
        "Document the current architecture",
        target=str(tmp_path),
        persist=True,
        cwd=tmp_path,
    )

    store = service.repository.load()

    for history in store.history.values():
        assert len(history) <= 1

