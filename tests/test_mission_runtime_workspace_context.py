import logging
from pathlib import Path

import pytest

from forge.memory import JsonMemoryStore
from forge.mission_runtime.errors import MissionScopeError
from forge.mission_runtime.workspace_context import (
    build_workspace_context,
    resolve_workspace,
)
from forge.workspace.manager import WorkspaceManager
from forge.workspace.models import ProjectType


def manager(tmp_path: Path) -> WorkspaceManager:
    return WorkspaceManager(
        JsonMemoryStore(tmp_path / "memory.json"),
        logging.getLogger("test-mission-runtime"),
    )


def test_workspace_context_resolves_active_repository(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    service = manager(tmp_path)
    workspace = service.register(
        "ERP",
        repository,
        ProjectType.ERP,
    )

    resolved = resolve_workspace(
        manager=service,
        workspace_id=workspace.workspace_id,
        repository_root=str(repository),
    )
    context = build_workspace_context(resolved)

    assert context.workspace_id == workspace.workspace_id
    assert context.technology.project_type is ProjectType.ERP


def test_workspace_context_rejects_scope_mismatch(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    other = tmp_path / "other"
    other.mkdir()
    service = manager(tmp_path)
    workspace = service.register(
        "ERP",
        repository,
        ProjectType.ERP,
    )

    with pytest.raises(MissionScopeError):
        resolve_workspace(
            manager=service,
            workspace_id=workspace.workspace_id,
            repository_root=str(other),
        )