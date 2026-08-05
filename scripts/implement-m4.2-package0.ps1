[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

function Write-Utf8NoBom {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$Content
    )

    $FullPath = Join-Path $RepositoryRoot $Path
    $Directory = Split-Path $FullPath -Parent
    New-Item -ItemType Directory -Path $Directory -Force | Out-Null

    [System.IO.File]::WriteAllText(
        $FullPath,
        $Content,
        [System.Text.UTF8Encoding]::new($false)
    )

    Write-Host "WROTE $Path" -ForegroundColor Green
}

function Assert-CommandSuccess {
    param([Parameter(Mandatory)][string]$Name)

    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

Write-Utf8NoBom "forge\domain_intelligence\backend\errors.py" @'
"""Typed errors for M4.2 Backend Domain Intelligence."""

from __future__ import annotations

from forge.domain_intelligence.errors import DomainIntelligenceError


class BackendIntelligenceError(DomainIntelligenceError):
    """Base error for backend-intelligence operations."""


class BackendConfigurationError(BackendIntelligenceError):
    """Raised when backend configuration is invalid."""


class BackendPolicyError(BackendIntelligenceError):
    """Raised when backend analysis violates policy."""


class BackendManifestError(BackendIntelligenceError):
    """Raised when backend project metadata is malformed."""
'@

Write-Utf8NoBom "forge\domain_intelligence\backend\identifiers.py" @'
"""Deterministic identifiers for M4.2 Backend Intelligence."""

from __future__ import annotations

from typing import Any

from forge.domain_intelligence.identifiers import stable_identifier


def backend_project_identifier(payload: Any) -> str:
    """Return a deterministic backend-project identifier."""
    return stable_identifier("backend-project", payload)


def backend_finding_identifier(payload: Any) -> str:
    """Return a deterministic backend-finding identifier."""
    return stable_identifier("backend-finding", payload)


def backend_report_identifier(payload: Any) -> str:
    """Return a deterministic backend-report identifier."""
    return stable_identifier("backend-report", payload)
'@

Write-Utf8NoBom "forge\domain_intelligence\backend\models.py" @'
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
'@

Write-Utf8NoBom "forge\domain_intelligence\backend\policies.py" @'
"""Safety policies for M4.2 Backend Domain Intelligence."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from forge.domain_intelligence.backend.errors import BackendPolicyError
from forge.domain_intelligence.backend.models import (
    BackendAnalysisRequest,
)


class BackendIntelligencePolicy(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    allow_network: bool = False
    allow_process_execution: bool = False
    allow_source_modification: bool = False
    inspect_secrets: bool = False
    require_repository_root: bool = True
    max_files: int = Field(default=7500, ge=1, le=100000)


def resolve_backend_repository_root(
    repository_root: str | Path,
    policy: BackendIntelligencePolicy,
) -> Path:
    """Resolve and validate the backend repository root."""
    root = Path(repository_root).expanduser().resolve()

    if not root.is_dir():
        raise BackendPolicyError(
            f"repository root does not exist: {root}"
        )

    if policy.require_repository_root and not (root / ".git").exists():
        raise BackendPolicyError(
            f"repository root is not a Git repository: {root}"
        )

    return root


def validate_backend_request(
    request: BackendAnalysisRequest,
    policy: BackendIntelligencePolicy,
) -> None:
    """Validate request bounds and repository-relative scope."""
    if request.max_files > policy.max_files:
        raise BackendPolicyError(
            f"request exceeds maximum file count: {policy.max_files}"
        )

    project_root = Path(request.project_root)

    if project_root.is_absolute() or ".." in project_root.parts:
        raise BackendPolicyError(
            "project root must remain repository-relative"
        )
'@

Write-Utf8NoBom "forge\domain_intelligence\backend\__init__.py" @'
"""M4.2 Backend Domain Intelligence public API."""

from forge.domain_intelligence.backend.errors import (
    BackendConfigurationError,
    BackendIntelligenceError,
    BackendManifestError,
    BackendPolicyError,
)
from forge.domain_intelligence.backend.identifiers import (
    backend_finding_identifier,
    backend_project_identifier,
    backend_report_identifier,
)
from forge.domain_intelligence.backend.models import (
    BackendAnalysisReport,
    BackendAnalysisRequest,
    BackendFinding,
    BackendFindingSeverity,
    BackendFramework,
    BackendProject,
    BackendRuntime,
)
from forge.domain_intelligence.backend.policies import (
    BackendIntelligencePolicy,
    resolve_backend_repository_root,
    validate_backend_request,
)

__all__ = [
    "BackendAnalysisReport",
    "BackendAnalysisRequest",
    "BackendConfigurationError",
    "BackendFinding",
    "BackendFindingSeverity",
    "BackendFramework",
    "BackendIntelligenceError",
    "BackendIntelligencePolicy",
    "BackendManifestError",
    "BackendPolicyError",
    "BackendProject",
    "BackendRuntime",
    "backend_finding_identifier",
    "backend_project_identifier",
    "backend_report_identifier",
    "resolve_backend_repository_root",
    "validate_backend_request",
]
'@

Write-Utf8NoBom "tests\test_domain_intelligence_backend_identifiers.py" @'
from forge.domain_intelligence.backend.identifiers import (
    backend_finding_identifier,
    backend_project_identifier,
)


def test_backend_project_identifier_is_deterministic() -> None:
    first = backend_project_identifier(
        {"root": "apps/api", "runtime": "nodejs"}
    )
    second = backend_project_identifier(
        {"runtime": "nodejs", "root": "apps/api"}
    )

    assert first == second
    assert first.startswith("backend-project-")


def test_backend_finding_identifier_changes_with_path() -> None:
    first = backend_finding_identifier({"path": "src/app.ts"})
    second = backend_finding_identifier({"path": "src/main.py"})

    assert first != second
'@

Write-Utf8NoBom "tests\test_domain_intelligence_backend_models.py" @'
import pytest
from pydantic import ValidationError

from forge.domain_intelligence.backend.models import (
    BackendAnalysisReport,
    BackendFinding,
    BackendFindingSeverity,
    BackendFramework,
    BackendProject,
    BackendRuntime,
)


def test_backend_project_supports_multiple_frameworks() -> None:
    project = BackendProject(
        project_id="backend-project-1",
        root="apps/api",
        runtimes=(BackendRuntime.NODEJS,),
        frameworks=(
            BackendFramework.NODE,
            BackendFramework.EXPRESS,
        ),
    )

    assert BackendFramework.EXPRESS in project.frameworks


def test_backend_report_rejects_duplicate_findings() -> None:
    project = BackendProject(
        project_id="backend-project-1",
        root="apps/api",
    )
    finding = BackendFinding(
        finding_id="backend-finding-1",
        category="framework",
        severity=BackendFindingSeverity.INFO,
        message="Express detected.",
    )

    with pytest.raises(ValidationError):
        BackendAnalysisReport(
            report_id="backend-report-1",
            project=project,
            findings=(finding, finding),
        )
'@

Write-Utf8NoBom "tests\test_domain_intelligence_backend_policies.py" @'
from pathlib import Path

import pytest

from forge.domain_intelligence.backend.errors import BackendPolicyError
from forge.domain_intelligence.backend.models import (
    BackendAnalysisRequest,
)
from forge.domain_intelligence.backend.policies import (
    BackendIntelligencePolicy,
    resolve_backend_repository_root,
    validate_backend_request,
)


def test_backend_policy_is_read_only_by_default() -> None:
    policy = BackendIntelligencePolicy()

    assert not policy.allow_network
    assert not policy.allow_process_execution
    assert not policy.allow_source_modification
    assert not policy.inspect_secrets


def test_backend_repository_requires_git(tmp_path: Path) -> None:
    with pytest.raises(BackendPolicyError):
        resolve_backend_repository_root(
            tmp_path,
            BackendIntelligencePolicy(),
        )


def test_backend_request_rejects_escape() -> None:
    request = BackendAnalysisRequest(
        repository_root=".",
        project_root="../outside",
    )

    with pytest.raises(BackendPolicyError):
        validate_backend_request(
            request,
            BackendIntelligencePolicy(),
        )
'@

Write-Utf8NoBom "docs\domain_intelligence\backend\ARCHITECTURE.md" @'
# M4.2 Backend Domain Intelligence Architecture

M4.2 provides read-only backend discovery and analysis through typed contracts,
framework detectors, service topology analysis, dependency inspection,
reporting, and CLI integration.

Package 0 establishes the immutable contracts and safety boundary. It does not
execute backend code, access the network, inspect secrets, or modify source.
'@

Write-Utf8NoBom "docs\domain_intelligence\backend\SPECIFICATION.md" @'
# M4.2 Backend Domain Intelligence Specification

Backend intelligence shall identify:

- Node.js and Python runtimes;
- Express, NestJS, FastAPI, Django, and Flask frameworks;
- package managers and dependency manifests;
- source, service, worker, and configuration files;
- backend architecture findings and evidence.

Analysis remains local, bounded, deterministic, and read-only.
'@

Write-Utf8NoBom "docs\domain_intelligence\backend\DATA_MODEL.md" @'
# M4.2 Backend Data Model

Primary contracts:

- BackendAnalysisRequest
- BackendProject
- BackendFinding
- BackendAnalysisReport
- BackendFramework
- BackendRuntime
- BackendFindingSeverity
- BackendIntelligencePolicy
'@

Write-Utf8NoBom "docs\domain_intelligence\backend\SECURITY_MODEL.md" @'
# M4.2 Backend Security Model

Backend analysis is fail-closed.

- Network access is disabled.
- Process execution is disabled.
- Source modification is disabled.
- Secret inspection is disabled.
- Repository path escape is rejected.
- File inspection is bounded.
- No application module is imported or executed during analysis.
'@

Write-Utf8NoBom "docs\domain_intelligence\backend\ACCEPTANCE_CRITERIA.md" @'
# M4.2 Package 0 Acceptance Criteria

- Backend contracts are immutable and typed.
- Backend identifiers are deterministic.
- Node.js and Python runtime types are represented.
- Supported backend frameworks are represented.
- Analysis is read-only and process-free by default.
- Repository path escape is rejected.
- Findings are unique within a report.
- Ruff, MyPy, focused tests, and full regression pass.
'@

Write-Host ""
Write-Host "M4.2 Package 0 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_domain_intelligence_backend_identifiers.py `
    .\tests\test_domain_intelligence_backend_models.py `
    .\tests\test_domain_intelligence_backend_policies.py `
    -p no:cacheprovider
Assert-CommandSuccess "M4.2 Package 0 tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M4.2 PACKAGE 0 COMPLETE" -ForegroundColor Green

git status --short
