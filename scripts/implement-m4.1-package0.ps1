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

Write-Utf8NoBom "forge\domain_intelligence\errors.py" @'
"""Typed errors for Phase 4 domain intelligence."""

from __future__ import annotations


class DomainIntelligenceError(Exception):
    """Base error for domain-intelligence operations."""


class DomainIntelligenceConfigurationError(DomainIntelligenceError):
    """Raised when domain-intelligence configuration is invalid."""


class DomainIntelligencePolicyError(DomainIntelligenceError):
    """Raised when analysis violates policy."""


class DomainIntelligenceValidationError(DomainIntelligenceError):
    """Raised when analysis evidence is invalid."""


class DomainPluginNotFoundError(DomainIntelligenceError):
    """Raised when a requested domain plugin is unavailable."""


class DomainPluginCompatibilityError(DomainIntelligenceError):
    """Raised when a plugin is incompatible with Forge."""


class FrontendAnalysisError(DomainIntelligenceError):
    """Raised when frontend analysis cannot complete safely."""
'@

Write-Utf8NoBom "forge\domain_intelligence\identifiers.py" @'
"""Deterministic identifiers for domain intelligence."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any


def _normalize(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _normalize(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }

    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return [_normalize(item) for item in value]

    if hasattr(value, "model_dump"):
        return _normalize(value.model_dump(mode="json"))

    if hasattr(value, "value"):
        return _normalize(value.value)

    return value


def stable_identifier(prefix: str, payload: Any) -> str:
    encoded = json.dumps(
        _normalize(payload),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")

    digest = hashlib.sha256(encoded).hexdigest()[:24]
    return f"{prefix}-{digest}"


def domain_plugin_identifier(payload: Any) -> str:
    return stable_identifier("domain-plugin", payload)


def frontend_project_identifier(payload: Any) -> str:
    return stable_identifier("frontend-project", payload)


def frontend_finding_identifier(payload: Any) -> str:
    return stable_identifier("frontend-finding", payload)


def frontend_report_identifier(payload: Any) -> str:
    return stable_identifier("frontend-report", payload)
'@

Write-Utf8NoBom "forge\domain_intelligence\models.py" @'
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
'@

Write-Utf8NoBom "forge\domain_intelligence\policies.py" @'
"""Policies for Phase 4 domain intelligence."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from forge.domain_intelligence.errors import DomainIntelligencePolicyError
from forge.domain_intelligence.models import FrontendAnalysisRequest


class DomainIntelligencePolicy(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    allow_network: bool = False
    allow_source_modification: bool = False
    require_repository_root: bool = True
    max_files: int = Field(default=5000, ge=1, le=100000)


def resolve_repository_root(
    repository_root: str | Path,
    policy: DomainIntelligencePolicy,
) -> Path:
    root = Path(repository_root).expanduser().resolve()

    if not root.is_dir():
        raise DomainIntelligencePolicyError(
            f"repository root does not exist: {root}"
        )

    if policy.require_repository_root and not (root / ".git").exists():
        raise DomainIntelligencePolicyError(
            f"repository root is not a Git repository: {root}"
        )

    return root


def validate_frontend_request(
    request: FrontendAnalysisRequest,
    policy: DomainIntelligencePolicy,
) -> None:
    if request.max_files > policy.max_files:
        raise DomainIntelligencePolicyError(
            f"request exceeds maximum file count: {policy.max_files}"
        )

    project_root = Path(request.project_root)

    if project_root.is_absolute() or ".." in project_root.parts:
        raise DomainIntelligencePolicyError(
            "project root must remain repository-relative"
        )
'@

Write-Utf8NoBom "forge\domain_intelligence\frontend\errors.py" @'
"""Frontend-intelligence errors."""

from forge.domain_intelligence.errors import FrontendAnalysisError

__all__ = ["FrontendAnalysisError"]
'@

Write-Utf8NoBom "forge\domain_intelligence\frontend\identifiers.py" @'
"""Frontend-intelligence identifiers."""

from forge.domain_intelligence.identifiers import (
    frontend_finding_identifier,
    frontend_project_identifier,
    frontend_report_identifier,
)

__all__ = [
    "frontend_finding_identifier",
    "frontend_project_identifier",
    "frontend_report_identifier",
]
'@

Write-Utf8NoBom "forge\domain_intelligence\frontend\models.py" @'
"""Frontend-intelligence public models."""

from forge.domain_intelligence.models import (
    FrontendAnalysisReport,
    FrontendAnalysisRequest,
    FrontendFinding,
    FrontendFindingSeverity,
    FrontendFramework,
    FrontendProject,
)

__all__ = [
    "FrontendAnalysisReport",
    "FrontendAnalysisRequest",
    "FrontendFinding",
    "FrontendFindingSeverity",
    "FrontendFramework",
    "FrontendProject",
]
'@

Write-Utf8NoBom "forge\domain_intelligence\frontend\policies.py" @'
"""Frontend-intelligence policies."""

from forge.domain_intelligence.policies import (
    DomainIntelligencePolicy,
    resolve_repository_root,
    validate_frontend_request,
)

__all__ = [
    "DomainIntelligencePolicy",
    "resolve_repository_root",
    "validate_frontend_request",
]
'@

Write-Utf8NoBom "forge\domain_intelligence\__init__.py" @'
"""Phase 4 domain-intelligence public API."""

from forge.domain_intelligence.errors import (
    DomainIntelligenceConfigurationError,
    DomainIntelligenceError,
    DomainIntelligencePolicyError,
    DomainIntelligenceValidationError,
    DomainPluginCompatibilityError,
    DomainPluginNotFoundError,
    FrontendAnalysisError,
)
from forge.domain_intelligence.identifiers import (
    domain_plugin_identifier,
    frontend_finding_identifier,
    frontend_project_identifier,
    frontend_report_identifier,
    stable_identifier,
)
from forge.domain_intelligence.models import (
    DomainKind,
    DomainPluginManifest,
    FrontendAnalysisReport,
    FrontendAnalysisRequest,
    FrontendFinding,
    FrontendFindingSeverity,
    FrontendFramework,
    FrontendProject,
)
from forge.domain_intelligence.policies import (
    DomainIntelligencePolicy,
    resolve_repository_root,
    validate_frontend_request,
)

__all__ = [
    "DomainIntelligenceConfigurationError",
    "DomainIntelligenceError",
    "DomainIntelligencePolicy",
    "DomainIntelligencePolicyError",
    "DomainIntelligenceValidationError",
    "DomainKind",
    "DomainPluginCompatibilityError",
    "DomainPluginManifest",
    "DomainPluginNotFoundError",
    "FrontendAnalysisError",
    "FrontendAnalysisReport",
    "FrontendAnalysisRequest",
    "FrontendFinding",
    "FrontendFindingSeverity",
    "FrontendFramework",
    "FrontendProject",
    "domain_plugin_identifier",
    "frontend_finding_identifier",
    "frontend_project_identifier",
    "frontend_report_identifier",
    "resolve_repository_root",
    "stable_identifier",
    "validate_frontend_request",
]
'@

Write-Utf8NoBom "forge\domain_intelligence\frontend\__init__.py" @'
"""M4.1 Frontend and UI Intelligence."""

from forge.domain_intelligence.frontend.errors import FrontendAnalysisError
from forge.domain_intelligence.frontend.identifiers import (
    frontend_finding_identifier,
    frontend_project_identifier,
    frontend_report_identifier,
)
from forge.domain_intelligence.frontend.models import (
    FrontendAnalysisReport,
    FrontendAnalysisRequest,
    FrontendFinding,
    FrontendFindingSeverity,
    FrontendFramework,
    FrontendProject,
)
from forge.domain_intelligence.frontend.policies import (
    DomainIntelligencePolicy,
    resolve_repository_root,
    validate_frontend_request,
)

__all__ = [
    "DomainIntelligencePolicy",
    "FrontendAnalysisError",
    "FrontendAnalysisReport",
    "FrontendAnalysisRequest",
    "FrontendFinding",
    "FrontendFindingSeverity",
    "FrontendFramework",
    "FrontendProject",
    "frontend_finding_identifier",
    "frontend_project_identifier",
    "frontend_report_identifier",
    "resolve_repository_root",
    "validate_frontend_request",
]
'@

Write-Utf8NoBom "tests\test_domain_intelligence_identifiers.py" @'
from forge.domain_intelligence.identifiers import (
    domain_plugin_identifier,
    frontend_project_identifier,
)


def test_domain_plugin_identifier_is_deterministic() -> None:
    first = domain_plugin_identifier({"name": "frontend", "version": "1.0"})
    second = domain_plugin_identifier({"version": "1.0", "name": "frontend"})

    assert first == second
    assert first.startswith("domain-plugin-")


def test_frontend_project_identifier_changes_with_root() -> None:
    first = frontend_project_identifier({"root": "apps/erp"})
    second = frontend_project_identifier({"root": "apps/crm"})

    assert first != second
'@

Write-Utf8NoBom "tests\test_domain_intelligence_models.py" @'
import pytest
from pydantic import ValidationError

from forge.domain_intelligence.models import (
    FrontendAnalysisReport,
    FrontendFinding,
    FrontendFindingSeverity,
    FrontendFramework,
    FrontendProject,
)


def test_frontend_project_accepts_multiple_frameworks() -> None:
    project = FrontendProject(
        project_id="project-1",
        root="apps/erp",
        frameworks=(FrontendFramework.REACT, FrontendFramework.VITE),
    )

    assert FrontendFramework.REACT in project.frameworks


def test_report_rejects_duplicate_findings() -> None:
    project = FrontendProject(project_id="project-1", root="apps/erp")
    finding = FrontendFinding(
        finding_id="finding-1",
        category="architecture",
        severity=FrontendFindingSeverity.MEDIUM,
        message="Example",
    )

    with pytest.raises(ValidationError):
        FrontendAnalysisReport(
            report_id="report-1",
            project=project,
            findings=(finding, finding),
        )
'@

Write-Utf8NoBom "tests\test_domain_intelligence_policies.py" @'
from pathlib import Path

import pytest

from forge.domain_intelligence.errors import DomainIntelligencePolicyError
from forge.domain_intelligence.models import FrontendAnalysisRequest
from forge.domain_intelligence.policies import (
    DomainIntelligencePolicy,
    resolve_repository_root,
    validate_frontend_request,
)


def test_repository_root_requires_git(tmp_path: Path) -> None:
    with pytest.raises(DomainIntelligencePolicyError):
        resolve_repository_root(tmp_path, DomainIntelligencePolicy())


def test_request_rejects_repository_escape() -> None:
    request = FrontendAnalysisRequest(
        repository_root=".",
        project_root="../outside",
    )

    with pytest.raises(DomainIntelligencePolicyError):
        validate_frontend_request(request, DomainIntelligencePolicy())


def test_request_respects_file_limit() -> None:
    request = FrontendAnalysisRequest(repository_root=".", max_files=100)

    with pytest.raises(DomainIntelligencePolicyError):
        validate_frontend_request(
            request,
            DomainIntelligencePolicy(max_files=10),
        )
'@

Write-Utf8NoBom "tests\test_domain_intelligence_frontend_identifiers.py" @'
from forge.domain_intelligence.frontend.identifiers import (
    frontend_report_identifier,
)


def test_frontend_report_identifier_has_expected_prefix() -> None:
    identifier = frontend_report_identifier({"project_id": "project-1"})

    assert identifier.startswith("frontend-report-")
'@

Write-Utf8NoBom "tests\test_domain_intelligence_frontend_models.py" @'
from forge.domain_intelligence.frontend.models import FrontendAnalysisRequest


def test_frontend_request_has_safe_defaults() -> None:
    request = FrontendAnalysisRequest(repository_root=".")

    assert "node_modules/**" in request.exclude_patterns
    assert request.max_files == 5000
'@

Write-Utf8NoBom "tests\test_domain_intelligence_frontend_policies.py" @'
from forge.domain_intelligence.frontend.policies import DomainIntelligencePolicy


def test_frontend_policy_is_read_only_by_default() -> None:
    policy = DomainIntelligencePolicy()

    assert not policy.allow_network
    assert not policy.allow_source_modification
'@

Write-Utf8NoBom "docs\domain_intelligence\ARCHITECTURE.md" @'
# Phase 4 Domain Intelligence Architecture

Forge Core remains domain-agnostic.

Domain-specific understanding is introduced through typed analyzers,
registries, manifests, policies, and knowledge packs under
`forge/domain_intelligence`.

M4.1 is the first implementation and adds read-only frontend intelligence.
'@

Write-Utf8NoBom "docs\domain_intelligence\SPECIFICATION.md" @'
# Phase 4 Domain Intelligence Specification

The framework shall:

- load domain intelligence without changing Forge Core semantics;
- use immutable typed contracts;
- generate deterministic identifiers;
- remain read-only by default;
- reject repository path escape;
- support versioned domain plugin manifests;
- produce auditable findings and reports.
'@

Write-Utf8NoBom "docs\domain_intelligence\DATA_MODEL.md" @'
# Phase 4 Domain Intelligence Data Model

Shared contracts:

- DomainPluginManifest
- FrontendAnalysisRequest
- FrontendProject
- FrontendFinding
- FrontendAnalysisReport
- DomainIntelligencePolicy
'@

Write-Utf8NoBom "docs\domain_intelligence\PLUGIN_MODEL.md" @'
# Phase 4 Plugin Model

Every domain plugin declares:

- stable identifier;
- name and version;
- domain kind;
- compatible Forge API version;
- declared capabilities;
- enabled state.

Plugins must not modify source code unless a later execution policy explicitly
authorizes it.
'@

Write-Utf8NoBom "docs\domain_intelligence\SECURITY_MODEL.md" @'
# Phase 4 Security Model

Domain analysis is fail-closed and read-only.

- Network access is disabled by default.
- Source modification is disabled by default.
- Repository escape is rejected.
- File counts are bounded.
- Plugin compatibility must be validated.
- Findings must preserve evidence.
'@

Write-Utf8NoBom "docs\domain_intelligence\COMPATIBILITY_MODEL.md" @'
# Phase 4 Compatibility Model

Domain plugins declare a Forge API version.

A plugin may load only when its declared API version is compatible with the
running Forge version and all required capabilities are available.
'@

Write-Utf8NoBom "docs\domain_intelligence\ACCEPTANCE_CRITERIA.md" @'
# Phase 4 Shared Acceptance Criteria

- Domain-intelligence contracts are immutable.
- Identifiers are deterministic.
- Analysis is read-only by default.
- Repository path escape is rejected.
- File analysis is bounded.
- Plugin manifests are explicit and versioned.
- Ruff, MyPy, focused tests, and full regression pass.
'@

Write-Utf8NoBom "docs\domain_intelligence\frontend\ARCHITECTURE.md" @'
# M4.1 Frontend Intelligence Architecture

M4.1 introduces a read-only frontend analysis layer for React, Vite, Next.js,
routing, components, hooks, state management, and styling.

Package 0 establishes shared contracts and policy boundaries only.
'@

Write-Utf8NoBom "docs\domain_intelligence\frontend\SPECIFICATION.md" @'
# M4.1 Frontend Intelligence Specification

Frontend analysis shall identify project roots, frameworks, package managers,
configuration files, source directories, routes, components, hooks, state
management, and styling technologies without modifying the repository.
'@

Write-Utf8NoBom "docs\domain_intelligence\frontend\DATA_MODEL.md" @'
# M4.1 Frontend Data Model

- FrontendAnalysisRequest
- FrontendProject
- FrontendFinding
- FrontendAnalysisReport
- FrontendFramework
- FrontendFindingSeverity
'@

Write-Utf8NoBom "docs\domain_intelligence\frontend\SECURITY_MODEL.md" @'
# M4.1 Frontend Security Model

Frontend analysis is local and read-only. It excludes dependency and generated
directories by default and enforces bounded file inspection.
'@

Write-Utf8NoBom "docs\domain_intelligence\frontend\ACCEPTANCE_CRITERIA.md" @'
# M4.1 Package 0 Acceptance Criteria

- Shared domain errors and identifiers exist.
- Plugin manifests are typed.
- Frontend requests and reports are typed.
- Read-only policy defaults are enforced.
- Repository path escape is rejected.
- Frontend package exports are stable.
- Ruff, MyPy, focused tests, and full regression pass.
'@

Write-Host ""
Write-Host "M4.1 Package 0 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_domain_intelligence_identifiers.py `
    .\tests\test_domain_intelligence_models.py `
    .\tests\test_domain_intelligence_policies.py `
    .\tests\test_domain_intelligence_frontend_identifiers.py `
    .\tests\test_domain_intelligence_frontend_models.py `
    .\tests\test_domain_intelligence_frontend_policies.py `
    -p no:cacheprovider
Assert-CommandSuccess "M4.1 Package 0 tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M4.1 PACKAGE 0 COMPLETE" -ForegroundColor Green

git status --short
