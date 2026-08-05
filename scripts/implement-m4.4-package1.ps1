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

Write-Utf8NoBom "forge\domain_intelligence\api\rest.py" @'
"""REST route discovery for M4.4 API Domain Intelligence."""

from __future__ import annotations

import re
from pathlib import Path

from forge.domain_intelligence.api.identifiers import (
    api_endpoint_identifier,
    api_finding_identifier,
)
from forge.domain_intelligence.api.models import (
    ApiEndpoint,
    ApiFinding,
    ApiFindingSeverity,
    HttpMethod,
)

_ROUTE_PATTERNS = (
    re.compile(
        r"""@(?:app|router)\.(?P<method>get|post|put|patch|delete|options|head)\(
        \s*["'](?P<path>[^"']+)["']""",
        re.IGNORECASE | re.VERBOSE,
    ),
    re.compile(
        r"""(?:app|router)\.(?P<method>get|post|put|patch|delete|options|head)\(
        \s*["'](?P<path>[^"']+)["']""",
        re.IGNORECASE | re.VERBOSE,
    ),
)


def discover_rest_endpoints(
    project_root: Path,
) -> tuple[ApiEndpoint, ...]:
    """Discover REST endpoints from local source files."""
    endpoints: dict[tuple[str, str], ApiEndpoint] = {}

    for path in project_root.rglob("*"):
        if not path.is_file():
            continue

        if path.suffix.lower() not in {".py", ".ts", ".js"}:
            continue

        if any(
            excluded in path.parts
            for excluded in (
                ".git",
                ".venv",
                "venv",
                "node_modules",
                "__pycache__",
                "dist",
                "build",
            )
        ):
            continue

        try:
            source = path.read_text(encoding="utf-8-sig")
        except OSError:
            continue

        relative = path.relative_to(project_root).as_posix()

        for pattern in _ROUTE_PATTERNS:
            for match in pattern.finditer(source):
                method = HttpMethod(
                    match.group("method").upper()
                )
                route = match.group("path")
                key = (method.value, route)

                endpoints[key] = ApiEndpoint(
                    endpoint_id=api_endpoint_identifier(
                        {
                            "method": method.value,
                            "path": route,
                            "source_path": relative,
                        }
                    ),
                    path=route,
                    method=method,
                    source_path=relative,
                )

    return tuple(
        sorted(
            endpoints.values(),
            key=lambda endpoint: (
                endpoint.path,
                endpoint.method.value,
            ),
        )
    )


def rest_findings(
    project_root: Path,
) -> tuple[ApiFinding, ...]:
    """Produce REST discovery findings."""
    endpoints = discover_rest_endpoints(project_root)

    if not endpoints:
        return ()

    finding_id = api_finding_identifier(
        {
            "category": "rest",
            "endpoint_ids": [
                endpoint.endpoint_id
                for endpoint in endpoints
            ],
        }
    )

    return (
        ApiFinding(
            finding_id=finding_id,
            category="rest",
            severity=ApiFindingSeverity.INFO,
            message="REST endpoints detected.",
            evidence={
                "endpoint_count": str(len(endpoints)),
                "paths": ",".join(
                    endpoint.path for endpoint in endpoints
                ),
            },
        ),
    )
'@

Write-Utf8NoBom "forge\domain_intelligence\api\openapi.py" @'
"""OpenAPI discovery and parsing for M4.4."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from forge.domain_intelligence.api.identifiers import (
    api_contract_identifier,
    api_endpoint_identifier,
    api_finding_identifier,
)
from forge.domain_intelligence.api.models import (
    ApiContract,
    ApiEndpoint,
    ApiFinding,
    ApiFindingSeverity,
    ApiResponse,
    ApiStyle,
    HttpMethod,
)

_OPENAPI_NAMES = {
    "openapi.json",
    "openapi.yaml",
    "openapi.yml",
    "swagger.json",
    "swagger.yaml",
    "swagger.yml",
}


def discover_openapi_files(
    project_root: Path,
) -> tuple[str, ...]:
    """Discover OpenAPI and Swagger contract files."""
    files: set[str] = set()

    for path in project_root.rglob("*"):
        if not path.is_file():
            continue

        if any(
            excluded in path.parts
            for excluded in (
                ".git",
                ".venv",
                "venv",
                "node_modules",
                "__pycache__",
                "dist",
                "build",
            )
        ):
            continue

        if path.name.lower() in _OPENAPI_NAMES:
            files.add(
                path.relative_to(project_root).as_posix()
            )

    return tuple(sorted(files))


def _load_document(path: Path) -> dict[str, Any]:
    if path.suffix.lower() == ".json":
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    else:
        raw = yaml.safe_load(
            path.read_text(encoding="utf-8-sig")
        )

    return raw if isinstance(raw, dict) else {}


def parse_openapi_file(
    project_root: Path,
    relative_path: str,
) -> ApiContract:
    """Parse one local OpenAPI or Swagger contract."""
    path = project_root / relative_path
    document = _load_document(path)

    info = document.get("info")
    info_mapping = info if isinstance(info, dict) else {}

    title = str(info_mapping.get("title") or path.stem)
    version_value = info_mapping.get("version")
    version = (
        str(version_value)
        if version_value is not None
        else None
    )

    endpoints: list[ApiEndpoint] = []
    paths = document.get("paths")
    path_mapping = paths if isinstance(paths, dict) else {}

    for route, operations in path_mapping.items():
        if not isinstance(route, str):
            continue

        if not isinstance(operations, dict):
            continue

        for method_name, operation in operations.items():
            normalized = str(method_name).upper()

            if normalized not in HttpMethod.__members__:
                continue

            method = HttpMethod[normalized]
            operation_mapping = (
                operation
                if isinstance(operation, dict)
                else {}
            )
            responses_raw = operation_mapping.get("responses")
            responses_mapping = (
                responses_raw
                if isinstance(responses_raw, dict)
                else {}
            )

            responses = tuple(
                ApiResponse(
                    status_code=str(status),
                    description=str(
                        value.get("description", "")
                    )
                    if isinstance(value, dict)
                    else "",
                )
                for status, value in sorted(
                    responses_mapping.items(),
                    key=lambda item: str(item[0]),
                )
            )

            endpoints.append(
                ApiEndpoint(
                    endpoint_id=api_endpoint_identifier(
                        {
                            "method": method.value,
                            "path": route,
                            "source_path": relative_path,
                        }
                    ),
                    path=route,
                    method=method,
                    operation_id=(
                        str(operation_mapping["operationId"])
                        if "operationId" in operation_mapping
                        else None
                    ),
                    summary=(
                        str(operation_mapping["summary"])
                        if "summary" in operation_mapping
                        else None
                    ),
                    responses=responses,
                    tags=tuple(
                        str(tag)
                        for tag in operation_mapping.get(
                            "tags",
                            (),
                        )
                        if isinstance(tag, str)
                    ),
                    source_path=relative_path,
                )
            )

    contract_id = api_contract_identifier(
        {
            "title": title,
            "version": version,
            "source_path": relative_path,
            "endpoint_ids": [
                endpoint.endpoint_id
                for endpoint in endpoints
            ],
        }
    )

    return ApiContract(
        contract_id=contract_id,
        title=title,
        version=version,
        style=ApiStyle.OPENAPI,
        source_path=relative_path,
        endpoints=tuple(
            sorted(
                endpoints,
                key=lambda endpoint: (
                    endpoint.path,
                    endpoint.method.value,
                ),
            )
        ),
    )


def openapi_findings(
    project_root: Path,
) -> tuple[ApiFinding, ...]:
    """Produce OpenAPI discovery findings."""
    files = discover_openapi_files(project_root)

    if not files:
        return ()

    finding_id = api_finding_identifier(
        {
            "category": "openapi",
            "files": files,
        }
    )

    return (
        ApiFinding(
            finding_id=finding_id,
            category="openapi",
            severity=ApiFindingSeverity.INFO,
            message="OpenAPI contracts detected.",
            evidence={
                "file_count": str(len(files)),
                "files": ",".join(files),
            },
        ),
    )
'@

Write-Utf8NoBom "forge\domain_intelligence\api\discovery.py" @'
"""API artifact discovery for M4.4."""

from __future__ import annotations

from pathlib import Path

from forge.domain_intelligence.api.identifiers import (
    api_finding_identifier,
)
from forge.domain_intelligence.api.models import (
    ApiFinding,
    ApiFindingSeverity,
)


def discover_api_source_files(
    project_root: Path,
) -> tuple[str, ...]:
    """Discover likely API source files."""
    files: set[str] = set()

    for path in project_root.rglob("*"):
        if not path.is_file():
            continue

        if path.suffix.lower() not in {
            ".py",
            ".ts",
            ".js",
            ".graphql",
            ".gql",
        }:
            continue

        if any(
            excluded in path.parts
            for excluded in (
                ".git",
                ".venv",
                "venv",
                "node_modules",
                "__pycache__",
                "dist",
                "build",
            )
        ):
            continue

        relative = path.relative_to(project_root).as_posix()
        lowered = relative.lower()

        if any(
            token in lowered
            for token in (
                "api",
                "route",
                "router",
                "controller",
                "endpoint",
                "graphql",
                "schema",
            )
        ):
            files.add(relative)

    return tuple(sorted(files))


def discovery_findings(
    project_root: Path,
) -> tuple[ApiFinding, ...]:
    """Produce API source discovery findings."""
    files = discover_api_source_files(project_root)

    if not files:
        return ()

    finding_id = api_finding_identifier(
        {
            "category": "source",
            "files": files,
        }
    )

    return (
        ApiFinding(
            finding_id=finding_id,
            category="source",
            severity=ApiFindingSeverity.INFO,
            message="API source files detected.",
            evidence={
                "file_count": str(len(files)),
                "files": ",".join(files),
            },
        ),
    )
'@

Write-Utf8NoBom "forge\domain_intelligence\api\registry.py" @'
"""Analyzer registry for M4.4 API Domain Intelligence."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path

from forge.domain_intelligence.api.errors import (
    ApiConfigurationError,
)
from forge.domain_intelligence.api.models import ApiFinding

ApiAnalyzer = Callable[[Path], tuple[ApiFinding, ...]]


class ApiAnalyzerRegistry:
    """Deterministic registry of named API analyzers."""

    def __init__(
        self,
        analyzers: Iterable[
            tuple[str, ApiAnalyzer]
        ] = (),
    ) -> None:
        self._analyzers: dict[str, ApiAnalyzer] = {}

        for name, analyzer in analyzers:
            self.register(name, analyzer)

    def register(
        self,
        name: str,
        analyzer: ApiAnalyzer,
    ) -> None:
        normalized = name.strip().lower()

        if not normalized:
            raise ApiConfigurationError(
                "API analyzer name cannot be empty"
            )

        if normalized in self._analyzers:
            raise ApiConfigurationError(
                f"duplicate API analyzer: {normalized}"
            )

        self._analyzers[normalized] = analyzer

    def names(self) -> tuple[str, ...]:
        """Return analyzer names in deterministic order."""
        return tuple(sorted(self._analyzers))

    def analyze(
        self,
        project_root: Path,
    ) -> tuple[ApiFinding, ...]:
        """Run all analyzers and return stable findings."""
        findings: list[ApiFinding] = []

        for name in self.names():
            findings.extend(
                self._analyzers[name](project_root)
            )

        return tuple(
            sorted(
                findings,
                key=lambda finding: finding.finding_id,
            )
        )
'@

Write-Utf8NoBom "forge\domain_intelligence\api\service.py" @'
"""API discovery service for M4.4 Package 1."""

from __future__ import annotations

from forge.domain_intelligence.api.discovery import (
    discover_api_source_files,
    discovery_findings,
)
from forge.domain_intelligence.api.identifiers import (
    api_contract_identifier,
    api_project_identifier,
    api_report_identifier,
)
from forge.domain_intelligence.api.models import (
    ApiAnalysisReport,
    ApiAnalysisRequest,
    ApiContract,
    ApiProject,
    ApiStyle,
)
from forge.domain_intelligence.api.openapi import (
    discover_openapi_files,
    openapi_findings,
    parse_openapi_file,
)
from forge.domain_intelligence.api.policies import (
    ApiIntelligencePolicy,
    resolve_api_repository_root,
    validate_api_request,
)
from forge.domain_intelligence.api.registry import (
    ApiAnalyzerRegistry,
)
from forge.domain_intelligence.api.rest import (
    discover_rest_endpoints,
    rest_findings,
)


def default_api_registry() -> ApiAnalyzerRegistry:
    """Return the M4.4 Package 1 analyzer registry."""
    return ApiAnalyzerRegistry(
        (
            ("discovery", discovery_findings),
            ("openapi", openapi_findings),
            ("rest", rest_findings),
        )
    )


class ApiIntelligenceService:
    """Discover API contracts and source endpoints safely."""

    def __init__(
        self,
        policy: ApiIntelligencePolicy | None = None,
        registry: ApiAnalyzerRegistry | None = None,
    ) -> None:
        self.policy = policy or ApiIntelligencePolicy()
        self.registry = registry or default_api_registry()

    def analyze(
        self,
        request: ApiAnalysisRequest,
    ) -> ApiAnalysisReport:
        """Run REST and OpenAPI discovery without network calls."""
        validate_api_request(request, self.policy)

        repository_root = resolve_api_repository_root(
            request.repository_root,
            self.policy,
        )
        project_root = (
            repository_root / request.project_root
        ).resolve()

        try:
            project_root.relative_to(repository_root)
        except ValueError as exc:
            raise ValueError(
                "resolved API project root escaped repository"
            ) from exc

        contracts = [
            parse_openapi_file(project_root, relative_path)
            for relative_path in discover_openapi_files(
                project_root
            )
        ]

        rest_endpoints = discover_rest_endpoints(project_root)

        if rest_endpoints:
            contracts.append(
                ApiContract(
                    contract_id=api_contract_identifier(
                        {
                            "title": "Discovered REST API",
                            "source_path": "source",
                            "endpoint_ids": [
                                endpoint.endpoint_id
                                for endpoint in rest_endpoints
                            ],
                        }
                    ),
                    title="Discovered REST API",
                    style=ApiStyle.REST,
                    source_path="source",
                    endpoints=rest_endpoints,
                )
            )

        styles = {
            contract.style for contract in contracts
        }

        project_payload = {
            "root": request.project_root,
            "styles": sorted(style.value for style in styles),
            "contract_files": discover_openapi_files(
                project_root
            ),
            "source_files": discover_api_source_files(
                project_root
            ),
        }

        project = ApiProject(
            project_id=api_project_identifier(project_payload),
            root=request.project_root,
            styles=tuple(
                sorted(
                    styles,
                    key=lambda style: style.value,
                )
            )
            or (ApiStyle.UNKNOWN,),
            contract_files=tuple(
                project_payload["contract_files"]
            ),
            source_files=tuple(
                project_payload["source_files"]
            ),
        )

        findings = self.registry.analyze(project_root)

        return ApiAnalysisReport(
            report_id=api_report_identifier(
                {
                    "project_id": project.project_id,
                    "contract_ids": [
                        contract.contract_id
                        for contract in contracts
                    ],
                    "finding_ids": [
                        finding.finding_id
                        for finding in findings
                    ],
                }
            ),
            project=project,
            contracts=tuple(
                sorted(
                    contracts,
                    key=lambda contract: (
                        contract.style.value,
                        contract.source_path,
                    ),
                )
            ),
            findings=findings,
        )
'@

Write-Utf8NoBom "tests\test_domain_intelligence_api_rest.py" @'
from pathlib import Path

from forge.domain_intelligence.api.models import HttpMethod
from forge.domain_intelligence.api.rest import (
    discover_rest_endpoints,
)


def test_discover_rest_endpoints(tmp_path: Path) -> None:
    (tmp_path / "routes.py").write_text(
        """
        @router.get("/orders")
        def list_orders():
            return []
        """,
        encoding="utf-8",
    )

    endpoints = discover_rest_endpoints(tmp_path)

    assert len(endpoints) == 1
    assert endpoints[0].path == "/orders"
    assert endpoints[0].method is HttpMethod.GET
'@

Write-Utf8NoBom "tests\test_domain_intelligence_api_openapi.py" @'
from pathlib import Path

from forge.domain_intelligence.api.models import (
    ApiStyle,
    HttpMethod,
)
from forge.domain_intelligence.api.openapi import (
    discover_openapi_files,
    parse_openapi_file,
)


def test_openapi_discovery_and_parsing(
    tmp_path: Path,
) -> None:
    (tmp_path / "openapi.yaml").write_text(
        """
        openapi: 3.0.0
        info:
          title: ERP API
          version: 1.0.0
        paths:
          /orders:
            get:
              operationId: listOrders
              responses:
                "200":
                  description: Success
        """,
        encoding="utf-8",
    )

    assert discover_openapi_files(tmp_path) == (
        "openapi.yaml",
    )

    contract = parse_openapi_file(
        tmp_path,
        "openapi.yaml",
    )

    assert contract.style is ApiStyle.OPENAPI
    assert contract.title == "ERP API"
    assert contract.endpoints[0].method is HttpMethod.GET
'@

Write-Utf8NoBom "tests\test_domain_intelligence_api_discovery.py" @'
from pathlib import Path

from forge.domain_intelligence.api.discovery import (
    discover_api_source_files,
)


def test_discover_api_source_files(tmp_path: Path) -> None:
    api = tmp_path / "api"
    api.mkdir()

    (api / "routes.py").write_text(
        "@router.get('/health')",
        encoding="utf-8",
    )

    assert discover_api_source_files(tmp_path) == (
        "api/routes.py",
    )
'@

Write-Utf8NoBom "tests\test_domain_intelligence_api_registry.py" @'
from pathlib import Path

import pytest

from forge.domain_intelligence.api.errors import (
    ApiConfigurationError,
)
from forge.domain_intelligence.api.models import ApiFinding
from forge.domain_intelligence.api.registry import (
    ApiAnalyzerRegistry,
)


def empty_analyzer(
    project_root: Path,
) -> tuple[ApiFinding, ...]:
    del project_root
    return ()


def test_api_registry_names_are_sorted() -> None:
    registry = ApiAnalyzerRegistry(
        (
            ("rest", empty_analyzer),
            ("openapi", empty_analyzer),
        )
    )

    assert registry.names() == (
        "openapi",
        "rest",
    )


def test_api_registry_rejects_duplicates() -> None:
    with pytest.raises(ApiConfigurationError):
        ApiAnalyzerRegistry(
            (
                ("rest", empty_analyzer),
                ("REST", empty_analyzer),
            )
        )
'@

Write-Utf8NoBom "tests\test_domain_intelligence_api_service.py" @'
from pathlib import Path

from forge.domain_intelligence.api.models import (
    ApiAnalysisRequest,
    ApiStyle,
)
from forge.domain_intelligence.api.service import (
    ApiIntelligenceService,
    default_api_registry,
)


def initialize_repository(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()


def test_default_api_registry() -> None:
    assert default_api_registry().names() == (
        "discovery",
        "openapi",
        "rest",
    )


def test_service_discovers_rest_and_openapi(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)

    (tmp_path / "openapi.yaml").write_text(
        """
        openapi: 3.0.0
        info:
          title: ERP API
          version: 1.0.0
        paths:
          /orders:
            get:
              responses:
                "200":
                  description: Success
        """,
        encoding="utf-8",
    )
    (tmp_path / "routes.py").write_text(
        """
        @router.post("/orders")
        def create_order():
            return {}
        """,
        encoding="utf-8",
    )

    report = ApiIntelligenceService().analyze(
        ApiAnalysisRequest(
            repository_root=str(tmp_path),
        )
    )

    assert report.project.styles == (
        ApiStyle.OPENAPI,
        ApiStyle.REST,
    )
    assert len(report.contracts) == 2


def test_service_reports_unknown_api(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)

    report = ApiIntelligenceService().analyze(
        ApiAnalysisRequest(
            repository_root=str(tmp_path),
        )
    )

    assert report.project.styles == (
        ApiStyle.UNKNOWN,
    )
'@

Write-Host ""
Write-Host "M4.4 Package 1 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_domain_intelligence_api_rest.py `
    .\tests\test_domain_intelligence_api_openapi.py `
    .\tests\test_domain_intelligence_api_discovery.py `
    .\tests\test_domain_intelligence_api_registry.py `
    .\tests\test_domain_intelligence_api_service.py `
    -p no:cacheprovider
Assert-CommandSuccess "M4.4 Package 1 tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M4.4 PACKAGE 1 COMPLETE" -ForegroundColor Green

git status --short
