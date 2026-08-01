"""Repository discovery domain models."""

from pathlib import Path

from pydantic import BaseModel, Field


class DiscoveredApplication(BaseModel):
    """An application or library inferred from repository structure."""

    name: str
    path: str
    kind: str
    technologies: list[str] = Field(default_factory=list)


class DiscoveredDependency(BaseModel):
    """A dependency declared by a recognized manifest."""

    name: str
    version: str | None = None
    scope: str = "runtime"
    source: str


class DirectoryEntry(BaseModel):
    """Aggregate statistics for one repository directory."""

    path: str
    files: int = Field(ge=0)
    directories: int = Field(ge=0)
    size_bytes: int = Field(ge=0)


class DiscoveryResult(BaseModel):
    """Complete deterministic repository discovery output."""

    repository_name: str
    repository_root: Path
    project_type: str
    languages: dict[str, int] = Field(default_factory=dict)
    frameworks: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    applications: list[DiscoveredApplication] = Field(default_factory=list)
    libraries: list[str] = Field(default_factory=list)
    microservices: list[str] = Field(default_factory=list)
    dependencies: list[DiscoveredDependency] = Field(default_factory=list)
    package_managers: list[str] = Field(default_factory=list)
    build_systems: list[str] = Field(default_factory=list)
    scripts: dict[str, str] = Field(default_factory=dict)
    test_frameworks: list[str] = Field(default_factory=list)
    linting: list[str] = Field(default_factory=list)
    formatting: list[str] = Field(default_factory=list)
    databases: list[str] = Field(default_factory=list)
    docker: bool = False
    docker_compose: bool = False
    kubernetes_manifests: list[str] = Field(default_factory=list)
    ci_cd: list[str] = Field(default_factory=list)
    configuration_files: list[str] = Field(default_factory=list)
    environment_files: list[str] = Field(default_factory=list)
    documentation: list[str] = Field(default_factory=list)
    license_file: str | None = None
    git: bool = False
    repository_size_bytes: int = Field(ge=0)
    file_count: int = Field(ge=0)
    directory_count: int = Field(ge=0)
    directory_structure: list[DirectoryEntry] = Field(default_factory=list)
    workspace_compatible: bool = True
