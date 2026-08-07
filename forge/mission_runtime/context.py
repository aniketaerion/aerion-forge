"""Repository-grounded mission context contracts."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from forge.workspace.models import ProjectType, WorkspaceHealth, WorkspaceStatus


class MissionTechnologyContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    project_type: ProjectType
    technologies: tuple[str, ...] = ()
    primary_language: str | None = None
    framework: str | None = None
    database: str | None = None
    package_manager: str | None = None
    build_system: str | None = None
    test_framework: str | None = None
    docker_enabled: bool = False
    git_enabled: bool = False


class MissionWorkspaceContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    workspace_id: str
    workspace_name: str
    repository_root: str
    status: WorkspaceStatus
    health: WorkspaceHealth
    technology: MissionTechnologyContext


class MissionCapabilitySelection(BaseModel):
    model_config = ConfigDict(frozen=True)

    capability_ids: tuple[str, ...] = ()
    unavailable_capability_ids: tuple[str, ...] = ()
    rationale: tuple[str, ...] = ()
    repository_grounded: bool = True


class MissionEngineeringContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    workspace: MissionWorkspaceContext
    capabilities: MissionCapabilitySelection
    context_references: tuple[str, ...] = Field(default_factory=tuple)