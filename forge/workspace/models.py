"""Validated workspace domain models."""

from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ProjectType(StrEnum):
    """Project categories supported by the workspace registry."""

    ERP = "ERP"
    CRM = "CRM"
    GCS = "GCS"
    PX4 = "PX4"
    ROS2 = "ROS2"
    PYTHON = "Python"
    REACT = "React"
    NODE = "Node"
    NEXTJS = "NextJS"
    EXPRESS = "Express"
    NESTJS = "NestJS"
    WEBSITE = "Website"
    FLUTTER = "Flutter"
    EMBEDDED = "Embedded"
    CPP = "C++"
    RUST = "Rust"
    GO = "Go"
    JAVA = "Java"
    GENERIC = "Generic"


class WorkspaceStatus(StrEnum):
    """Operational state derived from workspace validation."""

    READY = "ready"
    DEGRADED = "degraded"
    BROKEN = "broken"


class WorkspaceHealth(StrEnum):
    """Human-readable workspace health classification."""

    HEALTHY = "healthy"
    WARNING = "warning"
    UNHEALTHY = "unhealthy"


class TechnologyProfile(BaseModel):
    """Lightweight technology signals detected at a repository root."""

    technologies: list[str] = Field(default_factory=list)
    primary_language: str | None = None
    framework: str | None = None
    database: str | None = None
    package_manager: str | None = None
    build_system: str | None = None
    test_framework: str | None = None
    docker_enabled: bool = False
    git_enabled: bool = False


class Workspace(BaseModel):
    """Persistent metadata for one software project."""

    workspace_id: str
    name: str = Field(min_length=1, max_length=100)
    repository_path: Path
    project_type: ProjectType = ProjectType.GENERIC
    description: str = ""
    primary_language: str | None = None
    framework: str | None = None
    database: str | None = None
    package_manager: str | None = None
    build_system: str | None = None
    test_framework: str | None = None
    docker_enabled: bool = False
    git_enabled: bool = False
    created_date: datetime = Field(default_factory=lambda: datetime.now(UTC))
    modified_date: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_accessed: datetime | None = None
    status: WorkspaceStatus = WorkspaceStatus.READY
    health: WorkspaceHealth = WorkspaceHealth.HEALTHY
    tags: list[str] = Field(default_factory=list)
    notes: str = ""
    technologies: list[str] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        """Reject blank names and normalize surrounding whitespace."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("Workspace name cannot be blank")
        return normalized

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, values: list[str]) -> list[str]:
        """Store unique, non-empty tags while preserving input order."""
        return list(dict.fromkeys(value.strip() for value in values if value.strip()))


class DiagnosticCheck(BaseModel):
    """One workspace doctor check."""

    name: str
    available: bool
    detail: str


class WorkspaceDiagnostics(BaseModel):
    """Complete diagnostic result for a workspace."""

    workspace_id: str
    checks: list[DiagnosticCheck]
    missing_dependencies: list[str]
    workspace_health: WorkspaceHealth
    overall_status: WorkspaceStatus

    def as_mapping(self) -> dict[str, Any]:
        """Return checks keyed by their display names for CLI rendering."""
        return {check.name: check.model_dump() for check in self.checks}
