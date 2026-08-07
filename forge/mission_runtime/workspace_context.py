"""Workspace resolution for M5.8 mission runtime."""

from __future__ import annotations

from forge.mission_runtime.context import MissionWorkspaceContext
from forge.mission_runtime.errors import MissionScopeError
from forge.mission_runtime.technology_detection import (
    technology_context_from_workspace,
)
from forge.workspace.manager import WorkspaceManager
from forge.workspace.models import Workspace, WorkspaceStatus


def resolve_workspace(
    *,
    manager: WorkspaceManager,
    workspace_id: str,
    repository_root: str,
) -> Workspace:
    """Resolve and validate the mission workspace."""
    workspace = manager.load(workspace_id)
    expected = workspace.repository_path.resolve()
    actual = manager._validate_path(
        workspace.repository_path
    )

    if actual != expected:
        raise MissionScopeError(
            "Validated workspace path changed unexpectedly."
        )

    requested = repository_root.strip()

    if requested and actual != workspace.repository_path.__class__(
        requested
    ).resolve():
        raise MissionScopeError(
            "Mission repository does not match workspace repository."
        )

    if workspace.status is WorkspaceStatus.BROKEN:
        raise MissionScopeError(
            "Mission cannot use a broken workspace."
        )

    return workspace


def build_workspace_context(
    workspace: Workspace,
) -> MissionWorkspaceContext:
    """Build immutable mission workspace context."""
    return MissionWorkspaceContext(
        workspace_id=workspace.workspace_id,
        workspace_name=workspace.name,
        repository_root=str(workspace.repository_path.resolve()),
        status=workspace.status,
        health=workspace.health,
        technology=technology_context_from_workspace(
            workspace
        ),
    )