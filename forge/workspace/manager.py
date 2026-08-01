"""Persistent workspace lifecycle management."""

from __future__ import annotations

import builtins
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import ValidationError

from forge.memory import JsonMemoryStore
from forge.workspace.detection import detect_technologies, executable_available
from forge.workspace.errors import (
    DuplicateWorkspaceError,
    WorkspaceNotFoundError,
    WorkspaceValidationError,
)
from forge.workspace.models import (
    DiagnosticCheck,
    ProjectType,
    Workspace,
    WorkspaceDiagnostics,
    WorkspaceHealth,
    WorkspaceStatus,
)


class WorkspaceManager:
    """Manage durable workspace metadata through the Forge memory architecture."""

    def __init__(self, store: JsonMemoryStore, logger: logging.Logger) -> None:
        self.store = store
        self.logger = logger

    def register(
        self,
        name: str,
        repository_path: Path,
        project_type: ProjectType = ProjectType.GENERIC,
        description: str = "",
        tags: list[str] | None = None,
        notes: str = "",
    ) -> Workspace:
        """Validate, detect, and persist a new workspace."""
        root = self._validate_path(repository_path)
        self._ensure_unique(name, root)
        profile = detect_technologies(root)
        status, health = self._health(root, profile.git_enabled)
        workspace = Workspace(
            workspace_id=uuid4().hex,
            name=name,
            repository_path=root,
            project_type=project_type,
            description=description,
            tags=tags or [],
            notes=notes,
            status=status,
            health=health,
            **profile.model_dump(),
        )
        records = self._records()
        records[workspace.workspace_id] = workspace.model_dump(mode="json")
        self.store.set("workspaces", records)
        self.logger.info(
            "Workspace created",
            extra={"context": {"workspace_id": workspace.workspace_id, "name": workspace.name}},
        )
        return workspace

    def update(self, reference: str, **changes: Any) -> Workspace:
        """Update editable metadata and refresh detection when the path changes."""
        workspace = self.load(reference)
        permitted = {"repository_path", "project_type", "description", "tags", "notes"}
        invalid = set(changes) - permitted
        if invalid:
            raise WorkspaceValidationError(
                f"Unsupported workspace fields: {', '.join(sorted(invalid))}"
            )
        data = workspace.model_dump()
        data.update({key: value for key, value in changes.items() if value is not None})
        if "repository_path" in changes and changes["repository_path"] is not None:
            root = self._validate_path(Path(changes["repository_path"]))
            self._ensure_unique(workspace.name, root, exclude_id=workspace.workspace_id)
            profile = detect_technologies(root)
            data.update(profile.model_dump())
            data["repository_path"] = root
            data["status"], data["health"] = self._health(root, profile.git_enabled)
        data["modified_date"] = datetime.now(UTC)
        try:
            updated = Workspace.model_validate(data)
        except ValidationError as exc:
            raise WorkspaceValidationError(str(exc)) from exc
        self._save(updated)
        self.logger.info(
            "Workspace updated", extra={"context": {"workspace_id": updated.workspace_id}}
        )
        return updated

    def rename(self, reference: str, new_name: str) -> Workspace:
        """Rename a workspace while enforcing case-insensitive uniqueness."""
        workspace = self.load(reference)
        self._ensure_unique(new_name, workspace.repository_path, exclude_id=workspace.workspace_id)
        updated = workspace.model_copy(
            update={"name": new_name.strip(), "modified_date": datetime.now(UTC)}
        )
        updated = Workspace.model_validate(updated.model_dump())
        self._save(updated)
        self.logger.info(
            "Workspace renamed",
            extra={"context": {"workspace_id": updated.workspace_id, "name": updated.name}},
        )
        return updated

    def delete(self, reference: str) -> Workspace:
        """Remove a workspace record without modifying its repository."""
        workspace = self.load(reference)
        records = self._records()
        del records[workspace.workspace_id]
        self.store.set("workspaces", records)
        if self.store.read("active_workspace_id") == workspace.workspace_id:
            self.store.set("active_workspace_id", None)
        self.logger.info(
            "Workspace removed", extra={"context": {"workspace_id": workspace.workspace_id}}
        )
        return workspace

    def select(self, reference: str) -> Workspace:
        """Select a workspace as active and record its access time."""
        workspace = self.load(reference)
        workspace = workspace.model_copy(update={"last_accessed": datetime.now(UTC)})
        self._save(workspace)
        self.store.set("active_workspace_id", workspace.workspace_id)
        self.logger.info(
            "Workspace selected", extra={"context": {"workspace_id": workspace.workspace_id}}
        )
        return workspace

    def current(self) -> Workspace | None:
        """Return the selected workspace, if any."""
        identifier = self.store.read("active_workspace_id")
        return self.load(str(identifier)) if identifier else None

    def list(self) -> list[Workspace]:
        """Return all workspaces ordered by name."""
        workspaces = [self._parse(value) for value in self._records().values()]
        return sorted(workspaces, key=lambda item: item.name.casefold())

    def load(self, reference: str) -> Workspace:
        """Load a workspace by ID or case-insensitive name."""
        normalized = reference.casefold()
        for identifier, value in self._records().items():
            workspace = self._parse(value)
            if identifier == reference or workspace.name.casefold() == normalized:
                return workspace
        raise WorkspaceNotFoundError(f"Workspace not found: {reference}")

    def search(self, query: str) -> builtins.list[Workspace]:
        """Search workspace names, paths, descriptions, types, and tags."""
        term = query.casefold()
        return [
            workspace
            for workspace in self.list()
            if term
            in " ".join(
                (
                    workspace.name,
                    str(workspace.repository_path),
                    workspace.description,
                    workspace.project_type.value,
                    *workspace.tags,
                )
            ).casefold()
        ]

    def validate(self, reference: str) -> Workspace:
        """Revalidate a workspace path and refresh its health and technology metadata."""
        workspace = self.load(reference)
        try:
            root = self._validate_path(workspace.repository_path)
            profile = detect_technologies(root)
            status, health = self._health(root, profile.git_enabled)
            updated = workspace.model_copy(
                update={
                    **profile.model_dump(),
                    "status": status,
                    "health": health,
                    "modified_date": datetime.now(UTC),
                }
            )
        except WorkspaceValidationError:
            updated = workspace.model_copy(
                update={
                    "status": WorkspaceStatus.BROKEN,
                    "health": WorkspaceHealth.UNHEALTHY,
                    "modified_date": datetime.now(UTC),
                }
            )
            self._save(updated)
            self.logger.exception(
                "Workspace validation failed",
                extra={"context": {"workspace_id": workspace.workspace_id}},
            )
            raise
        self._save(updated)
        self.logger.info(
            "Workspace validation completed",
            extra={"context": {"workspace_id": updated.workspace_id, "status": updated.status}},
        )
        return updated

    def doctor(self, reference: str) -> WorkspaceDiagnostics:
        """Return environment and repository diagnostics for a workspace."""
        workspace = self.validate(reference)
        technologies = set(workspace.technologies)
        checks = [
            DiagnosticCheck(
                name="Git", available=workspace.git_enabled, detail="repository marker"
            ),
            DiagnosticCheck(
                name="Docker",
                available=workspace.docker_enabled and executable_available("docker"),
                detail="repository configuration and executable",
            ),
            DiagnosticCheck(
                name="Python", available="Python" in technologies, detail="project marker"
            ),
            DiagnosticCheck(name="Node", available="Node" in technologies, detail="package.json"),
            DiagnosticCheck(
                name="Database",
                available=workspace.database is not None,
                detail=workspace.database or "not detected",
            ),
            DiagnosticCheck(
                name="Package Manager",
                available=workspace.package_manager is not None,
                detail=workspace.package_manager or "not detected",
            ),
        ]
        expected = [
            tool
            for tool in (workspace.package_manager, "docker" if workspace.docker_enabled else None)
            if tool and tool != "pip"
        ]
        missing = [tool for tool in expected if not executable_available(tool)]
        health = workspace.health if not missing else WorkspaceHealth.WARNING
        status = workspace.status if not missing else WorkspaceStatus.DEGRADED
        diagnostics = WorkspaceDiagnostics(
            workspace_id=workspace.workspace_id,
            checks=checks,
            missing_dependencies=missing,
            workspace_health=health,
            overall_status=status,
        )
        self.logger.info(
            "Workspace doctor completed",
            extra={"context": {"workspace_id": workspace.workspace_id, "status": status}},
        )
        return diagnostics

    def _save(self, workspace: Workspace) -> None:
        records = self._records()
        records[workspace.workspace_id] = workspace.model_dump(mode="json")
        self.store.set("workspaces", records)

    def _records(self) -> dict[str, Any]:
        records = self.store.read("workspaces")
        if records is None:
            return {}
        if not isinstance(records, dict):
            raise WorkspaceValidationError("Workspace registry must be a JSON object")
        return dict(records)

    @staticmethod
    def _parse(value: Any) -> Workspace:
        try:
            return Workspace.model_validate(value)
        except ValidationError as exc:
            raise WorkspaceValidationError(f"Invalid persisted workspace: {exc}") from exc

    def _ensure_unique(self, name: str, root: Path, exclude_id: str | None = None) -> None:
        normalized_name = name.strip().casefold()
        if not normalized_name:
            raise WorkspaceValidationError("Workspace name cannot be blank")
        for workspace in self.list():
            if workspace.workspace_id == exclude_id:
                continue
            if workspace.name.casefold() == normalized_name:
                raise DuplicateWorkspaceError(f"Workspace name already exists: {name.strip()}")
            if workspace.repository_path == root:
                raise DuplicateWorkspaceError(f"Repository is already registered: {root}")

    @staticmethod
    def _validate_path(path: Path) -> Path:
        try:
            root = path.expanduser().resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise WorkspaceValidationError(f"Repository path does not exist: {path}") from exc
        if not root.is_dir():
            raise WorkspaceValidationError(f"Repository path is not a directory: {root}")
        if not os.access(root, os.R_OK):
            raise WorkspaceValidationError(f"Repository path is not readable: {root}")
        return root

    @staticmethod
    def _health(root: Path, git_enabled: bool) -> tuple[WorkspaceStatus, WorkspaceHealth]:
        if not root.is_dir() or not os.access(root, os.R_OK):
            return WorkspaceStatus.BROKEN, WorkspaceHealth.UNHEALTHY
        if not git_enabled:
            return WorkspaceStatus.DEGRADED, WorkspaceHealth.WARNING
        return WorkspaceStatus.READY, WorkspaceHealth.HEALTHY
