import logging
from pathlib import Path

import pytest

from forge.memory import JsonMemoryStore
from forge.workspace import (
    DuplicateWorkspaceError,
    ProjectType,
    WorkspaceHealth,
    WorkspaceManager,
    WorkspaceStatus,
    WorkspaceValidationError,
)


def manager_at(path: Path) -> WorkspaceManager:
    logger = logging.getLogger(f"workspace-test-{path.name}")
    logger.handlers = [logging.NullHandler()]
    return WorkspaceManager(JsonMemoryStore(path / "workspaces.json"), logger)


def git_repository(path: Path) -> Path:
    path.mkdir()
    (path / ".git").mkdir()
    return path


def test_workspace_crud_persistence_search_and_switching(tmp_path: Path) -> None:
    repository = git_repository(tmp_path / "erp")
    manager = manager_at(tmp_path / "memory")
    workspace = manager.register(
        "ERP", repository, ProjectType.ERP, "Core platform", ["finance", "python"]
    )

    reloaded = manager_at(tmp_path / "memory")
    assert reloaded.load(workspace.workspace_id).name == "ERP"
    assert reloaded.search("finance")[0].workspace_id == workspace.workspace_id

    renamed = reloaded.rename("ERP", "Enterprise")
    updated = reloaded.update(
        renamed.workspace_id,
        description="Updated",
        project_type=ProjectType.PYTHON,
        tags=["platform"],
    )
    selected = reloaded.select("Enterprise")

    assert updated.description == "Updated"
    assert selected.last_accessed is not None
    current = reloaded.current()
    assert current is not None
    assert current.workspace_id == workspace.workspace_id

    removed = reloaded.delete(workspace.workspace_id)
    assert removed.name == "Enterprise"
    assert reloaded.list() == []
    assert reloaded.current() is None


def test_duplicate_name_and_path_are_rejected(tmp_path: Path) -> None:
    first = git_repository(tmp_path / "first")
    second = git_repository(tmp_path / "second")
    manager = manager_at(tmp_path / "memory")
    manager.register("ERP", first)

    with pytest.raises(DuplicateWorkspaceError, match="name"):
        manager.register("erp", second)
    with pytest.raises(DuplicateWorkspaceError, match="already registered"):
        manager.register("Other", first)


def test_invalid_and_broken_paths_are_reported(tmp_path: Path) -> None:
    manager = manager_at(tmp_path / "memory")
    with pytest.raises(WorkspaceValidationError, match="does not exist"):
        manager.register("Missing", tmp_path / "missing")

    repository = git_repository(tmp_path / "project")
    workspace = manager.register("Project", repository)
    (repository / ".git").rmdir()
    repository.rmdir()

    with pytest.raises(WorkspaceValidationError):
        manager.validate(workspace.workspace_id)
    persisted = manager.load(workspace.workspace_id)
    assert persisted.status is WorkspaceStatus.BROKEN
    assert persisted.health is WorkspaceHealth.UNHEALTHY


def test_detection_and_doctor_report_project_technologies(tmp_path: Path) -> None:
    repository = git_repository(tmp_path / "web")
    (repository / "package.json").write_text(
        '{"dependencies":{"react":"latest","pg":"latest"},'
        '"devDependencies":{"typescript":"latest"}}',
        encoding="utf-8",
    )
    (repository / "pnpm-lock.yaml").write_text("lockfileVersion: 9\n", encoding="utf-8")
    (repository / "Dockerfile").write_text("FROM node:22\n", encoding="utf-8")
    manager = manager_at(tmp_path / "memory")

    workspace = manager.register("Web", repository, ProjectType.REACT)
    diagnostics = manager.doctor("Web")

    assert {"Node", "React", "TypeScript", "Docker", "PostgreSQL", "pnpm"} <= set(
        workspace.technologies
    )
    assert workspace.framework == "React"
    assert workspace.database == "PostgreSQL"
    assert workspace.package_manager == "pnpm"
    assert {check.name for check in diagnostics.checks} == {
        "Git",
        "Docker",
        "Python",
        "Node",
        "Database",
        "Package Manager",
    }
