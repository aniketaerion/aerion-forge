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

Write-Utf8NoBom "forge\domain_intelligence\api\errors.py" @'
"""Typed errors for M4.4 API Domain Intelligence."""

from __future__ import annotations

from forge.domain_intelligence.errors import DomainIntelligenceError


class ApiIntelligenceError(DomainIntelligenceError):
    """Base error for API-intelligence operations."""


class ApiConfigurationError(ApiIntelligenceError):
    """Raised when API configuration is invalid."""


class ApiPolicyError(ApiIntelligenceError):
    """Raised when API analysis violates policy."""


class ApiParseError(ApiIntelligenceError):
    """Raised when an API artifact cannot be parsed safely."""
'@

Write-Utf8NoBom "forge\domain_intelligence\api\identifiers.py" @'
"""Deterministic identifiers for M4.4 API Domain Intelligence."""

from __future__ import annotations

from typing import Any

from forge.domain_intelligence.identifiers import stable_identifier


def api_project_identifier(payload: Any) -> str:
    """Return a deterministic API-project identifier."""
    return stable_identifier("api-project", payload)


def api_endpoint_identifier(payload: Any) -> str:
    """Return a deterministic API-endpoint identifier."""
    return stable_identifier("api-endpoint", payload)


def api_contract_identifier(payload: Any) -> str:
    """Return a deterministic API-contract identifier."""
    return stable_identifier("api-contract", payload)


def api_finding_identifier(payload: Any) -> str:
    """Return a deterministic API-finding identifier."""
    return stable_identifier("api-finding", payload)


def api_report_identifier(payload: Any) -> str:
    """Return a deterministic API-report identifier."""
    return stable_identifier("api-report", payload)
'@

Write-Utf8NoBom "forge\domain_intelligence\api\models.py" @'
"""Immutable contracts for M4.4 API Domain Intelligence."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ApiStyle(StrEnum):
    REST = "rest"
    OPENAPI = "openapi"
    GRAPHQL = "graphql"
    RPC = "rpc"
    WEBSOCKET = "websocket"
    UNKNOWN = "unknown"


class HttpMethod(StrEnum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    OPTIONS = "OPTIONS"
    HEAD = "HEAD"


class ApiAuthenticationKind(StrEnum):
    NONE = "none"
    API_KEY = "api_key"
    BASIC = "basic"
    BEARER = "bearer"
    OAUTH2 = "oauth2"
    COOKIE = "cookie"
    MUTUAL_TLS = "mutual_tls"
    UNKNOWN = "unknown"


class ApiFindingSeverity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ImmutableApiModel(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        str_strip_whitespace=True,
    )


class ApiAnalysisRequest(ImmutableApiModel):
    repository_root: str = Field(min_length=1)
    project_root: str = Field(default=".", min_length=1)
    include_patterns: tuple[str, ...] = (
        "**/*.json",
        "**/*.yaml",
        "**/*.yml",
        "**/*.py",
        "**/*.ts",
        "**/*.js",
        "**/*.graphql",
        "**/*.gql",
    )
    exclude_patterns: tuple[str, ...] = (
        ".git/**",
        "node_modules/**",
        ".venv/**",
        "venv/**",
        "__pycache__/**",
        "dist/**",
        "build/**",
    )
    max_files: int = Field(default=10000, ge=1, le=100000)


class ApiParameter(ImmutableApiModel):
    name: str = Field(min_length=1)
    location: str = Field(min_length=1)
    required: bool = False
    schema_type: str | None = None


class ApiResponse(ImmutableApiModel):
    status_code: str = Field(min_length=1)
    description: str = Field(min_length=1)
    schema_reference: str | None = None


class ApiEndpoint(ImmutableApiModel):
    endpoint_id: str = Field(min_length=1)
    path: str = Field(min_length=1)
    method: HttpMethod
    operation_id: str | None = None
    summary: str | None = None
    authentication: tuple[ApiAuthenticationKind, ...] = ()
    parameters: tuple[ApiParameter, ...] = ()
    responses: tuple[ApiResponse, ...] = ()
    tags: tuple[str, ...] = ()
    source_path: str | None = None


class ApiContract(ImmutableApiModel):
    contract_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    version: str | None = None
    style: ApiStyle
    source_path: str
    endpoints: tuple[ApiEndpoint, ...] = ()

    @field_validator("endpoints")
    @classmethod
    def ensure_unique_endpoints(
        cls,
        endpoints: tuple[ApiEndpoint, ...],
    ) -> tuple[ApiEndpoint, ...]:
        identifiers = [endpoint.endpoint_id for endpoint in endpoints]

        if len(identifiers) != len(set(identifiers)):
            raise ValueError("API endpoint identifiers must be unique")

        return endpoints


class ApiProject(ImmutableApiModel):
    project_id: str = Field(min_length=1)
    root: str = Field(min_length=1)
    styles: tuple[ApiStyle, ...] = ()
    contract_files: tuple[str, ...] = ()
    source_files: tuple[str, ...] = ()
    configuration_files: tuple[str, ...] = ()
    detected_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )


class ApiFinding(ImmutableApiModel):
    finding_id: str = Field(min_length=1)
    category: str = Field(min_length=1)
    severity: ApiFindingSeverity
    message: str = Field(min_length=1)
    path: str | None = None
    evidence: dict[str, str] = Field(default_factory=dict)


class ApiAnalysisReport(ImmutableApiModel):
    report_id: str = Field(min_length=1)
    project: ApiProject
    contracts: tuple[ApiContract, ...] = ()
    findings: tuple[ApiFinding, ...] = ()
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )

    @field_validator("findings")
    @classmethod
    def ensure_unique_findings(
        cls,
        findings: tuple[ApiFinding, ...],
    ) -> tuple[ApiFinding, ...]:
        identifiers = [finding.finding_id for finding in findings]

        if len(identifiers) != len(set(identifiers)):
            raise ValueError("API finding identifiers must be unique")

        return findings
'@

Write-Utf8NoBom "forge\domain_intelligence\api\policies.py" @'
"""Safety policies for M4.4 API Domain Intelligence."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from forge.domain_intelligence.api.errors import ApiPolicyError
from forge.domain_intelligence.api.models import ApiAnalysisRequest


class ApiIntelligencePolicy(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    allow_network: bool = False
    allow_remote_schema_fetch: bool = False
    allow_request_execution: bool = False
    allow_secret_inspection: bool = False
    allow_mutation: bool = False
    require_repository_root: bool = True
    max_files: int = Field(default=10000, ge=1, le=100000)
    max_file_bytes: int = Field(
        default=5_000_000,
        ge=1,
        le=100_000_000,
    )


def resolve_api_repository_root(
    repository_root: str | Path,
    policy: ApiIntelligencePolicy,
) -> Path:
    """Resolve and validate the API repository root."""
    root = Path(repository_root).expanduser().resolve()

    if not root.is_dir():
        raise ApiPolicyError(
            f"repository root does not exist: {root}"
        )

    if policy.require_repository_root and not (root / ".git").exists():
        raise ApiPolicyError(
            f"repository root is not a Git repository: {root}"
        )

    return root


def validate_api_request(
    request: ApiAnalysisRequest,
    policy: ApiIntelligencePolicy,
) -> None:
    """Validate API-analysis scope and bounds."""
    if request.max_files > policy.max_files:
        raise ApiPolicyError(
            f"request exceeds maximum file count: {policy.max_files}"
        )

    project_root = Path(request.project_root)

    if project_root.is_absolute() or ".." in project_root.parts:
        raise ApiPolicyError(
            "project root must remain repository-relative"
        )
'@

Write-Utf8NoBom "forge\domain_intelligence\api\__init__.py" @'
"""M4.4 API Domain Intelligence public API."""

from forge.domain_intelligence.api.errors import (
    ApiConfigurationError,
    ApiIntelligenceError,
    ApiParseError,
    ApiPolicyError,
)
from forge.domain_intelligence.api.identifiers import (
    api_contract_identifier,
    api_endpoint_identifier,
    api_finding_identifier,
    api_project_identifier,
    api_report_identifier,
)
from forge.domain_intelligence.api.models import (
    ApiAnalysisReport,
    ApiAnalysisRequest,
    ApiAuthenticationKind,
    ApiContract,
    ApiEndpoint,
    ApiFinding,
    ApiFindingSeverity,
    ApiParameter,
    ApiProject,
    ApiResponse,
    ApiStyle,
    HttpMethod,
)
from forge.domain_intelligence.api.policies import (
    ApiIntelligencePolicy,
    resolve_api_repository_root,
    validate_api_request,
)

__all__ = [
    "ApiAnalysisReport",
    "ApiAnalysisRequest",
    "ApiAuthenticationKind",
    "ApiConfigurationError",
    "ApiContract",
    "ApiEndpoint",
    "ApiFinding",
    "ApiFindingSeverity",
    "ApiIntelligenceError",
    "ApiIntelligencePolicy",
    "ApiParameter",
    "ApiParseError",
    "ApiPolicyError",
    "ApiProject",
    "ApiResponse",
    "ApiStyle",
    "HttpMethod",
    "api_contract_identifier",
    "api_endpoint_identifier",
    "api_finding_identifier",
    "api_project_identifier",
    "api_report_identifier",
    "resolve_api_repository_root",
    "validate_api_request",
]
'@

Write-Utf8NoBom "tests\test_domain_intelligence_api_identifiers.py" @'
from forge.domain_intelligence.api.identifiers import (
    api_endpoint_identifier,
    api_project_identifier,
)


def test_api_project_identifier_is_deterministic() -> None:
    first = api_project_identifier(
        {"root": "apps/api", "style": "rest"}
    )
    second = api_project_identifier(
        {"style": "rest", "root": "apps/api"}
    )

    assert first == second
    assert first.startswith("api-project-")


def test_api_endpoint_identifier_changes_by_method() -> None:
    first = api_endpoint_identifier(
        {"path": "/orders", "method": "GET"}
    )
    second = api_endpoint_identifier(
        {"path": "/orders", "method": "POST"}
    )

    assert first != second
'@

Write-Utf8NoBom "tests\test_domain_intelligence_api_models.py" @'
import pytest
from pydantic import ValidationError

from forge.domain_intelligence.api.models import (
    ApiAnalysisReport,
    ApiAuthenticationKind,
    ApiContract,
    ApiEndpoint,
    ApiFinding,
    ApiFindingSeverity,
    ApiProject,
    ApiStyle,
    HttpMethod,
)


def test_api_contract_supports_endpoint_metadata() -> None:
    endpoint = ApiEndpoint(
        endpoint_id="endpoint-1",
        path="/orders",
        method=HttpMethod.GET,
        authentication=(ApiAuthenticationKind.BEARER,),
        tags=("orders",),
    )
    contract = ApiContract(
        contract_id="contract-1",
        title="ERP API",
        version="1.0.0",
        style=ApiStyle.OPENAPI,
        source_path="openapi.yaml",
        endpoints=(endpoint,),
    )

    assert contract.endpoints[0].method is HttpMethod.GET


def test_api_contract_rejects_duplicate_endpoints() -> None:
    endpoint = ApiEndpoint(
        endpoint_id="endpoint-1",
        path="/orders",
        method=HttpMethod.GET,
    )

    with pytest.raises(ValidationError):
        ApiContract(
            contract_id="contract-1",
            title="ERP API",
            style=ApiStyle.REST,
            source_path="routes.py",
            endpoints=(endpoint, endpoint),
        )


def test_api_report_rejects_duplicate_findings() -> None:
    project = ApiProject(
        project_id="api-project-1",
        root="apps/api",
        styles=(ApiStyle.REST,),
    )
    finding = ApiFinding(
        finding_id="api-finding-1",
        category="security",
        severity=ApiFindingSeverity.HIGH,
        message="Missing authentication.",
    )

    with pytest.raises(ValidationError):
        ApiAnalysisReport(
            report_id="api-report-1",
            project=project,
            findings=(finding, finding),
        )
'@

Write-Utf8NoBom "tests\test_domain_intelligence_api_policies.py" @'
from pathlib import Path

import pytest

from forge.domain_intelligence.api.errors import ApiPolicyError
from forge.domain_intelligence.api.models import ApiAnalysisRequest
from forge.domain_intelligence.api.policies import (
    ApiIntelligencePolicy,
    resolve_api_repository_root,
    validate_api_request,
)


def test_api_policy_is_offline_and_read_only() -> None:
    policy = ApiIntelligencePolicy()

    assert not policy.allow_network
    assert not policy.allow_remote_schema_fetch
    assert not policy.allow_request_execution
    assert not policy.allow_secret_inspection
    assert not policy.allow_mutation


def test_api_repository_requires_git(tmp_path: Path) -> None:
    with pytest.raises(ApiPolicyError):
        resolve_api_repository_root(
            tmp_path,
            ApiIntelligencePolicy(),
        )


def test_api_request_rejects_path_escape() -> None:
    request = ApiAnalysisRequest(
        repository_root=".",
        project_root="../outside",
    )

    with pytest.raises(ApiPolicyError):
        validate_api_request(
            request,
            ApiIntelligencePolicy(),
        )
'@

Write-Utf8NoBom "docs\domain_intelligence\api\ARCHITECTURE.md" @'
# M4.4 API Domain Intelligence Architecture

M4.4 provides read-only API discovery and contract analysis through typed
contracts, REST and OpenAPI inspection, GraphQL analysis, dependency mapping,
versioning checks, authentication and security findings, reporting, and CLI
integration.

Package 0 establishes the immutable contracts and safety boundary. It does not
make network calls, invoke endpoints, fetch remote schemas, inspect secrets, or
modify source files.
'@

Write-Utf8NoBom "docs\domain_intelligence\api\SPECIFICATION.md" @'
# M4.4 API Domain Intelligence Specification

API intelligence shall identify:

- REST, OpenAPI, GraphQL, RPC, and WebSocket interfaces;
- routes, methods, parameters, responses, and tags;
- authentication and authorization declarations;
- API versions and compatibility signals;
- contract dependencies and security risks.

Analysis remains local, deterministic, bounded, offline, and read-only.
'@

Write-Utf8NoBom "docs\domain_intelligence\api\DATA_MODEL.md" @'
# M4.4 API Data Model

Primary contracts:

- ApiAnalysisRequest
- ApiProject
- ApiEndpoint
- ApiParameter
- ApiResponse
- ApiContract
- ApiFinding
- ApiAnalysisReport
- ApiIntelligencePolicy
'@

Write-Utf8NoBom "docs\domain_intelligence\api\SECURITY_MODEL.md" @'
# M4.4 API Security Model

API analysis is fail-closed.

- Network access is disabled.
- Remote schema fetching is disabled.
- Endpoint execution is disabled.
- Secret inspection is disabled.
- Source mutation is disabled.
- Repository path escape is rejected.
- File count and file-size limits are enforced.
'@

Write-Utf8NoBom "docs\domain_intelligence\api\ACCEPTANCE_CRITERIA.md" @'
# M4.4 Package 0 Acceptance Criteria

- API contracts are immutable and typed.
- API identifiers are deterministic.
- REST, OpenAPI, GraphQL, RPC, and WebSocket styles are represented.
- Endpoints, parameters, responses, and authentication are modeled.
- Duplicate endpoint and finding identifiers are rejected.
- Analysis is offline and read-only by default.
- Repository path escape is rejected.
- Ruff, MyPy, focused tests, and full regression pass.
'@

Write-Host ""
Write-Host "M4.4 Package 0 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_domain_intelligence_api_identifiers.py `
    .\tests\test_domain_intelligence_api_models.py `
    .\tests\test_domain_intelligence_api_policies.py `
    -p no:cacheprovider
Assert-CommandSuccess "M4.4 Package 0 tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M4.4 PACKAGE 0 COMPLETE" -ForegroundColor Green

git status --short
