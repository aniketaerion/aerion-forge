"""Immutable contracts for M4.2 Backend Domain Intelligence."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BackendFramework(StrEnum):
    NODE = "node"
    EXPRESS = "express"
    NESTJS = "nestjs"
    FASTAPI = "fastapi"
    DJANGO = "django"
    FLASK = "flask"
    UNKNOWN = "unknown"


class BackendRuntime(StrEnum):
    NODEJS = "nodejs"
    PYTHON = "python"
    UNKNOWN = "unknown"


class BackendFindingSeverity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ImmutableBackendModel(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        str_strip_whitespace=True,
    )


class BackendAnalysisRequest(ImmutableBackendModel):
    repository_root: str = Field(min_length=1)
    project_root: str = Field(default=".", min_length=1)
    include_patterns: tuple[str, ...] = (
        "**/*.js",
        "**/*.mjs",
        "**/*.cjs",
        "**/*.ts",
        "**/*.py",
        "**/*.json",
        "**/*.toml",
        "**/*.yaml",
        "**/*.yml",
    )
    exclude_patterns: tuple[str, ...] = (
        "node_modules/**",
        ".venv/**",
        "venv/**",
        "__pycache__/**",
        "dist/**",
        "build/**",
        ".git/**",
    )
    max_files: int = Field(default=7500, ge=1, le=100000)


class BackendProject(ImmutableBackendModel):
    project_id: str = Field(min_length=1)
    root: str = Field(min_length=1)
    runtimes: tuple[BackendRuntime, ...] = ()
    frameworks: tuple[BackendFramework, ...] = ()
    package_manager: str | None = None
    source_directories: tuple[str, ...] = ()
    configuration_files: tuple[str, ...] = ()
    service_files: tuple[str, ...] = ()
    worker_files: tuple[str, ...] = ()
    detected_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )


class BackendFinding(ImmutableBackendModel):
    finding_id: str = Field(min_length=1)
    category: str = Field(min_length=1)
    severity: BackendFindingSeverity
    message: str = Field(min_length=1)
    path: str | None = None
    evidence: dict[str, str] = Field(default_factory=dict)


class BackendAnalysisReport(ImmutableBackendModel):
    report_id: str = Field(min_length=1)
    project: BackendProject
    findings: tuple[BackendFinding, ...] = ()
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )

    @field_validator("findings")
    @classmethod
    def ensure_unique_findings(
        cls,
        findings: tuple[BackendFinding, ...],
    ) -> tuple[BackendFinding, ...]:
        identifiers = [finding.finding_id for finding in findings]

        if len(identifiers) != len(set(identifiers)):
            raise ValueError(
                "backend finding identifiers must be unique"
            )

        return findings