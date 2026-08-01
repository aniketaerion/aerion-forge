"""Workspace registration, detection, validation, and diagnostics API."""

from forge.workspace.errors import (
    DuplicateWorkspaceError,
    WorkspaceError,
    WorkspaceNotFoundError,
    WorkspaceValidationError,
)
from forge.workspace.manager import WorkspaceManager
from forge.workspace.models import (
    ProjectType,
    TechnologyProfile,
    Workspace,
    WorkspaceDiagnostics,
    WorkspaceHealth,
    WorkspaceStatus,
)

__all__ = [
    "DuplicateWorkspaceError",
    "ProjectType",
    "TechnologyProfile",
    "Workspace",
    "WorkspaceDiagnostics",
    "WorkspaceError",
    "WorkspaceHealth",
    "WorkspaceManager",
    "WorkspaceNotFoundError",
    "WorkspaceStatus",
    "WorkspaceValidationError",
]
