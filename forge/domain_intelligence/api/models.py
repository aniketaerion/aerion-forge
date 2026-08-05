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