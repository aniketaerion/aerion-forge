"""Strongly typed repository-audit domain models."""

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field


class FileRecord(BaseModel):
    """A classified repository file."""

    path: str
    category: str
    size_bytes: int = Field(ge=0)
    language: str | None = None


class DependencyNode(BaseModel):
    """A dependency declared by a project manifest."""

    name: str
    version: str | None = None
    scope: str = "runtime"
    source: str


class DependencyGraph(BaseModel):
    """Serializable dependency graph with project-to-package edges."""

    project: str
    nodes: list[DependencyNode] = Field(default_factory=list)
    edges: list[tuple[str, str]] = Field(default_factory=list)


class Finding(BaseModel):
    """An actionable audit observation."""

    category: str
    severity: str
    message: str
    path: str | None = None
    line: int | None = None


class RepositoryInventory(BaseModel):
    """Complete inventory and classifications for an audited repository."""

    root: str
    files: list[FileRecord] = Field(default_factory=list)
    languages: dict[str, int] = Field(default_factory=dict)
    technologies: list[str] = Field(default_factory=list)
    package_managers: list[str] = Field(default_factory=list)
    build_commands: list[str] = Field(default_factory=list)
    test_commands: list[str] = Field(default_factory=list)
    api_files: list[str] = Field(default_factory=list)
    route_files: list[str] = Field(default_factory=list)
    migrations: list[str] = Field(default_factory=list)
    documentation: list[str] = Field(default_factory=list)
    configuration: list[str] = Field(default_factory=list)
    environment_files: list[str] = Field(default_factory=list)
    ci_files: list[str] = Field(default_factory=list)
    docker_files: list[str] = Field(default_factory=list)
    backend_files: list[str] = Field(default_factory=list)
    frontend_files: list[str] = Field(default_factory=list)
    test_files: list[str] = Field(default_factory=list)


class AuditResult(BaseModel):
    """Aggregate result produced by the repository audit agent."""

    repository: str
    started_at: datetime
    completed_at: datetime
    inventory: RepositoryInventory
    dependency_graph: DependencyGraph
    findings: list[Finding] = Field(default_factory=list)
    reports: dict[str, Path] = Field(default_factory=dict)
