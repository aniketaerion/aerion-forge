"""Shared immutable contracts for Phase 4 domain intelligence."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DomainKind(StrEnum):
    FRONTEND = "frontend"
    BACKEND = "backend"
    DATABASE = "database"
    API = "api"
    BUSINESS = "business"
    EMBEDDED = "embedded"


class FrontendFramework(StrEnum):
    REACT = "react"
    VITE = "vite"
    NEXTJS = "nextjs"
    UNKNOWN = "unknown"


class FrontendFindingSeverity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ImmutableModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)


class DomainPluginManifest(ImmutableModel):
    plugin_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    domain: DomainKind
    forge_api_version: str = Field(min_length=1)
    capabilities: tuple[str, ...] = ()
    enabled: bool = True


class FrontendAnalysisRequest(ImmutableModel):
    repository_root: str = Field(min_length=1)
    project_root: str = Field(default=".", min_length=1)
    include_patterns: tuple[str, ...] = (
        "**/*.js",
        "**/*.jsx",
        "**/*.ts",
        "**/*.tsx",
        "**/*.css",
    )
    exclude_patterns: tuple[str, ...] = (
        "node_modules/**",
        "dist/**",
        "build/**",
        ".next/**",
    )
    max_files: int = Field(default=5000, ge=1, le=100000)


class FrontendProject(ImmutableModel):
    project_id: str = Field(min_length=1)
    root: str = Field(min_length=1)
    frameworks: tuple[FrontendFramework, ...] = ()
    package_manager: str | None = None
    source_directories: tuple[str, ...] = ()
    route_files: tuple[str, ...] = ()
    component_files: tuple[str, ...] = ()
    configuration_files: tuple[str, ...] = ()
    detected_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class FrontendFinding(ImmutableModel):
    finding_id: str = Field(min_length=1)
    category: str = Field(min_length=1)
    severity: FrontendFindingSeverity
    message: str = Field(min_length=1)
    path: str | None = None
    evidence: dict[str, str] = Field(default_factory=dict)


class FrontendAnalysisReport(ImmutableModel):
    report_id: str = Field(min_length=1)
    project: FrontendProject
    findings: tuple[FrontendFinding, ...] = ()
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("findings")
    @classmethod
    def ensure_unique_findings(
        cls,
        findings: tuple[FrontendFinding, ...],
    ) -> tuple[FrontendFinding, ...]:
        identifiers = [finding.finding_id for finding in findings]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("frontend finding identifiers must be unique")
        return findings