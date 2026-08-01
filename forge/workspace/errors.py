"""Workspace-specific domain errors."""


class WorkspaceError(Exception):
    """Base class for recoverable workspace operations."""


class WorkspaceNotFoundError(WorkspaceError):
    """Raised when a workspace reference cannot be resolved."""


class DuplicateWorkspaceError(WorkspaceError):
    """Raised when a workspace name or repository path already exists."""


class WorkspaceValidationError(WorkspaceError):
    """Raised when a repository cannot form a valid workspace."""
