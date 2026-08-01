"""Read-only target resolution using the established workspace order."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from forge.diagnostics.errors import DiagnosticTargetNotFoundError
from forge.memory import JsonMemoryStore
from forge.workspace.errors import WorkspaceNotFoundError
from forge.workspace.manager import WorkspaceManager
from forge.workspace.models import Workspace


class ResolvedDiagnosticTarget:
    def __init__(self, root: Path, identity: str, workspace: Workspace | None) -> None:
        self.root = root
        self.identity = identity
        self.workspace = workspace


def resolve_target(
    target: str | None, workspace_store: Path, logger: logging.Logger, current: Path | None = None
) -> ResolvedDiagnosticTarget:
    manager = WorkspaceManager(JsonMemoryStore(workspace_store), logger)
    workspace: Workspace | None = None
    if target is None:
        workspace = manager.current()
        root = workspace.repository_path if workspace else (current or Path.cwd())
    else:
        try:
            workspace = manager.load(target)
            root = workspace.repository_path
        except WorkspaceNotFoundError:
            candidate = Path(target).expanduser()
            if not candidate.exists() or not candidate.is_dir():
                raise DiagnosticTargetNotFoundError(
                    "Workspace or repository target was not found."
                ) from None
            root = candidate
    root = root.resolve()
    identity = (
        workspace.workspace_id
        if workspace
        else hashlib.sha256(str(root).casefold().encode("utf-8")).hexdigest()
    )
    return ResolvedDiagnosticTarget(root, identity, workspace)
