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

Write-Utf8NoBom "forge\domain_intelligence\api\graphql.py" @'
"""GraphQL discovery for M4.4 API Domain Intelligence."""

from __future__ import annotations

import re
from pathlib import Path

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
    ApiStyle,
    HttpMethod,
)

_GRAPHQL_TYPE_PATTERN = re.compile(
    r"\btype\s+(Query|Mutation|Subscription)\s*\{",
    re.IGNORECASE,
)


def discover_graphql_files(
    project_root: Path,
) -> tuple[str, ...]:
    """Discover GraphQL schema and resolver files."""
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

        if path.suffix.lower() in {".graphql", ".gql"}:
            files.add(path.relative_to(project_root).as_posix())
            continue

        if path.suffix.lower() not in {".py", ".ts", ".js"}:
            continue

        try:
            source = path.read_text(encoding="utf-8-sig")
        except OSError:
            continue

        lowered = source.lower()

        if any(
            marker in lowered
            for marker in (
                "graphql",
                "resolver",
                "typegraphql",
                "strawberry",
                "graphene",
            )
        ):
            files.add(path.relative_to(project_root).as_posix())

    return tuple(sorted(files))


def parse_graphql_contract(
    project_root: Path,
) -> ApiContract | None:
    """Build one local GraphQL contract from discovered schema files."""
    files = discover_graphql_files(project_root)
    schema_files = tuple(
        relative
        for relative in files
        if Path(relative).suffix.lower() in {".graphql", ".gql"}
    )

    if not schema_files:
        return None

    operations: set[str] = set()

    for relative in schema_files:
        try:
            source = (project_root / relative).read_text(
                encoding="utf-8-sig"
            )
        except OSError:
            continue

        operations.update(
            match.group(1).lower()
            for match in _GRAPHQL_TYPE_PATTERN.finditer(source)
        )

    endpoints = tuple(
        ApiEndpoint(
            endpoint_id=api_endpoint_identifier(
                {
                    "style": "graphql",
                    "operation": operation,
                    "path": "/graphql",
                }
            ),
            path="/graphql",
            method=HttpMethod.POST,
            operation_id=operation,
            tags=("graphql", operation),
            source_path=",".join(schema_files),
        )
        for operation in sorted(operations)
    )

    return ApiContract(
        contract_id=api_contract_identifier(
            {
                "style": "graphql",
                "schema_files": schema_files,
                "operations": sorted(operations),
            }
        ),
        title="Discovered GraphQL API",
        style=ApiStyle.GRAPHQL,
        source_path=",".join(schema_files),
        endpoints=endpoints,
    )


def graphql_findings(
    project_root: Path,
) -> tuple[ApiFinding, ...]:
    """Produce GraphQL discovery findings."""
    files = discover_graphql_files(project_root)

    if not files:
        return ()

    finding_id = api_finding_identifier(
        {
            "category": "graphql",
            "files": files,
        }
    )

    return (
        ApiFinding(
            finding_id=finding_id,
            category="graphql",
            severity=ApiFindingSeverity.INFO,
            message="GraphQL artifacts detected.",
            evidence={
                "file_count": str(len(files)),
                "files": ",".join(files),
            },
        ),
    )
'@

Write-Utf8NoBom "forge\domain_intelligence\api\dependencies.py" @'
"""API dependency analysis for M4.4."""

from __future__ import annotations

import json
from pathlib import Path

from forge.domain_intelligence.api.identifiers import (
    api_finding_identifier,
)
from forge.domain_intelligence.api.models import (
    ApiFinding,
    ApiFindingSeverity,
)

_API_DEPENDENCIES = {
    "apollo-server",
    "@apollo/server",
    "express",
    "fastapi",
    "flask",
    "graphene",
    "graphql",
    "nestjs",
    "strawberry-graphql",
}


def discover_api_dependencies(
    project_root: Path,
) -> tuple[str, ...]:
    """Discover known API framework dependencies."""
    dependencies: set[str] = set()

    package_json = project_root / "package.json"

    if package_json.is_file():
        try:
            document = json.loads(
                package_json.read_text(encoding="utf-8-sig")
            )
        except (OSError, json.JSONDecodeError):
            document = {}

        for section_name in (
            "dependencies",
            "devDependencies",
            "peerDependencies",
        ):
            section = document.get(section_name)

            if not isinstance(section, dict):
                continue

            dependencies.update(
                name
                for name in section
                if name in _API_DEPENDENCIES
            )

    for requirements_name in (
        "requirements.txt",
        "requirements-dev.txt",
    ):
        path = project_root / requirements_name

        if not path.is_file():
            continue

        try:
            lines = path.read_text(
                encoding="utf-8-sig"
            ).splitlines()
        except OSError:
            continue

        for line in lines:
            normalized = (
                line.split("==", maxsplit=1)[0]
                .split(">=", maxsplit=1)[0]
                .strip()
                .lower()
            )

            if normalized in _API_DEPENDENCIES:
                dependencies.add(normalized)

    return tuple(sorted(dependencies))


def dependency_findings(
    project_root: Path,
) -> tuple[ApiFinding, ...]:
    """Produce API dependency findings."""
    dependencies = discover_api_dependencies(project_root)

    if not dependencies:
        return ()

    finding_id = api_finding_identifier(
        {
            "category": "dependencies",
            "dependencies": dependencies,
        }
    )

    return (
        ApiFinding(
            finding_id=finding_id,
            category="dependencies",
            severity=ApiFindingSeverity.INFO,
            message="API framework dependencies detected.",
            evidence={
                "dependency_count": str(len(dependencies)),
                "dependencies": ",".join(dependencies),
            },
        ),
    )
'@

Write-Utf8NoBom "forge\domain_intelligence\api\versioning.py" @'
"""API version analysis for M4.4."""

from __future__ import annotations

import re

from forge.domain_intelligence.api.identifiers import (
    api_finding_identifier,
)
from forge.domain_intelligence.api.models import (
    ApiContract,
    ApiFinding,
    ApiFindingSeverity,
)

_PATH_VERSION_PATTERN = re.compile(
    r"/v(?P<version>[0-9]+)(?:/|$)",
    re.IGNORECASE,
)


def contract_versions(
    contracts: tuple[ApiContract, ...],
) -> tuple[str, ...]:
    """Return declared and path-derived API versions."""
    versions: set[str] = set()

    for contract in contracts:
        if contract.version:
            versions.add(contract.version)

        for endpoint in contract.endpoints:
            match = _PATH_VERSION_PATTERN.search(endpoint.path)
            if match is not None:
                versions.add(match.group("version"))

    return tuple(sorted(versions))


def versioning_findings(
    contracts: tuple[ApiContract, ...],
) -> tuple[ApiFinding, ...]:
    """Report missing or inconsistent API versioning."""
    versions = contract_versions(contracts)

    if not contracts:
        return ()

    findings: list[ApiFinding] = []

    if not versions:
        finding_id = api_finding_identifier(
            {"category": "missing_versioning"}
        )
        findings.append(
            ApiFinding(
                finding_id=finding_id,
                category="missing_versioning",
                severity=ApiFindingSeverity.MEDIUM,
                message="No API versioning signal was detected.",
            )
        )

    if len(versions) > 1:
        finding_id = api_finding_identifier(
            {
                "category": "multiple_versions",
                "versions": versions,
            }
        )
        findings.append(
            ApiFinding(
                finding_id=finding_id,
                category="multiple_versions",
                severity=ApiFindingSeverity.INFO,
                message="Multiple API versions were detected.",
                evidence={"versions": ",".join(versions)},
            )
        )

    return tuple(
        sorted(findings, key=lambda finding: finding.finding_id)
    )
'@

Write-Utf8NoBom "forge\domain_intelligence\api\compatibility.py" @'
"""API compatibility analysis for M4.4."""

from __future__ import annotations

from forge.domain_intelligence.api.identifiers import (
    api_finding_identifier,
)
from forge.domain_intelligence.api.models import (
    ApiContract,
    ApiFinding,
    ApiFindingSeverity,
)


def compatibility_findings(
    contracts: tuple[ApiContract, ...],
) -> tuple[ApiFinding, ...]:
    """Identify duplicate method-path contracts and operation identifiers."""
    findings: list[ApiFinding] = []
    route_owners: dict[tuple[str, str], list[str]] = {}
    operation_owners: dict[str, list[str]] = {}

    for contract in contracts:
        for endpoint in contract.endpoints:
            key = (endpoint.method.value, endpoint.path)
            route_owners.setdefault(key, []).append(
                contract.contract_id
            )

            if endpoint.operation_id:
                operation_owners.setdefault(
                    endpoint.operation_id,
                    [],
                ).append(endpoint.endpoint_id)

    for (method, path), owners in sorted(route_owners.items()):
        if len(owners) <= 1:
            continue

        finding_id = api_finding_identifier(
            {
                "category": "duplicate_route_contract",
                "method": method,
                "path": path,
                "owners": owners,
            }
        )
        findings.append(
            ApiFinding(
                finding_id=finding_id,
                category="duplicate_route_contract",
                severity=ApiFindingSeverity.MEDIUM,
                message=(
                    "The same method and path appear in multiple "
                    "API contracts."
                ),
                evidence={
                    "method": method,
                    "path": path,
                    "contract_count": str(len(owners)),
                },
            )
        )

    for operation_id, endpoint_ids in sorted(
        operation_owners.items()
    ):
        if len(endpoint_ids) <= 1:
            continue

        finding_id = api_finding_identifier(
            {
                "category": "duplicate_operation_id",
                "operation_id": operation_id,
                "endpoint_ids": endpoint_ids,
            }
        )
        findings.append(
            ApiFinding(
                finding_id=finding_id,
                category="duplicate_operation_id",
                severity=ApiFindingSeverity.HIGH,
                message="Duplicate API operation identifier detected.",
                evidence={
                    "operation_id": operation_id,
                    "endpoint_count": str(len(endpoint_ids)),
                },
            )
        )

    return tuple(
        sorted(findings, key=lambda finding: finding.finding_id)
    )
'@

Write-Utf8NoBom "forge\domain_intelligence\api\security.py" @'
"""API security analysis for M4.4."""

from __future__ import annotations

from forge.domain_intelligence.api.identifiers import (
    api_finding_identifier,
)
from forge.domain_intelligence.api.models import (
    ApiAuthenticationKind,
    ApiContract,
    ApiFinding,
    ApiFindingSeverity,
)


def security_findings(
    contracts: tuple[ApiContract, ...],
) -> tuple[ApiFinding, ...]:
    """Identify conservative API authentication risks."""
    findings: list[ApiFinding] = []

    for contract in contracts:
        for endpoint in contract.endpoints:
            authentication = set(endpoint.authentication)

            if authentication and authentication != {
                ApiAuthenticationKind.NONE
            }:
                continue

            finding_id = api_finding_identifier(
                {
                    "category": "missing_authentication",
                    "endpoint_id": endpoint.endpoint_id,
                }
            )

            findings.append(
                ApiFinding(
                    finding_id=finding_id,
                    category="missing_authentication",
                    severity=ApiFindingSeverity.HIGH,
                    message=(
                        "No authentication requirement was detected "
                        f"for {endpoint.method.value} {endpoint.path}."
                    ),
                    path=endpoint.source_path,
                    evidence={
                        "method": endpoint.method.value,
                        "path": endpoint.path,
                    },
                )
            )

    return tuple(
        sorted(findings, key=lambda finding: finding.finding_id)
    )
'@

Write-Utf8NoBom "tests\test_domain_intelligence_api_graphql.py" @'
from pathlib import Path

from forge.domain_intelligence.api.graphql import (
    discover_graphql_files,
    parse_graphql_contract,
)
from forge.domain_intelligence.api.models import ApiStyle


def test_graphql_discovery_and_contract(
    tmp_path: Path,
) -> None:
    (tmp_path / "schema.graphql").write_text(
        """
        type Query {
            orders: [Order!]!
        }

        type Mutation {
            createOrder: Order!
        }
        """,
        encoding="utf-8",
    )

    assert discover_graphql_files(tmp_path) == (
        "schema.graphql",
    )

    contract = parse_graphql_contract(tmp_path)

    assert contract is not None
    assert contract.style is ApiStyle.GRAPHQL
    assert {
        endpoint.operation_id
        for endpoint in contract.endpoints
    } == {"query", "mutation"}
'@

Write-Utf8NoBom "tests\test_domain_intelligence_api_dependencies.py" @'
import json
from pathlib import Path

from forge.domain_intelligence.api.dependencies import (
    discover_api_dependencies,
)


def test_discover_api_dependencies(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        json.dumps(
            {
                "dependencies": {
                    "express": "^5.0.0",
                    "graphql": "^16.0.0",
                    "react": "^19.0.0",
                }
            }
        ),
        encoding="utf-8",
    )

    assert discover_api_dependencies(tmp_path) == (
        "express",
        "graphql",
    )
'@

Write-Utf8NoBom "tests\test_domain_intelligence_api_versioning.py" @'
from forge.domain_intelligence.api.models import (
    ApiContract,
    ApiEndpoint,
    ApiStyle,
    HttpMethod,
)
from forge.domain_intelligence.api.versioning import (
    contract_versions,
    versioning_findings,
)


def test_contract_versions_and_multiple_version_finding() -> None:
    contract = ApiContract(
        contract_id="contract-1",
        title="ERP API",
        version="1.0.0",
        style=ApiStyle.REST,
        source_path="routes.py",
        endpoints=(
            ApiEndpoint(
                endpoint_id="endpoint-1",
                path="/v2/orders",
                method=HttpMethod.GET,
            ),
        ),
    )

    assert contract_versions((contract,)) == (
        "1.0.0",
        "2",
    )
    assert {
        finding.category
        for finding in versioning_findings((contract,))
    } == {"multiple_versions"}
'@

Write-Utf8NoBom "tests\test_domain_intelligence_api_compatibility.py" @'
from forge.domain_intelligence.api.compatibility import (
    compatibility_findings,
)
from forge.domain_intelligence.api.models import (
    ApiContract,
    ApiEndpoint,
    ApiStyle,
    HttpMethod,
)


def test_compatibility_detects_duplicate_routes() -> None:
    first = ApiContract(
        contract_id="contract-1",
        title="First API",
        style=ApiStyle.REST,
        source_path="routes.py",
        endpoints=(
            ApiEndpoint(
                endpoint_id="endpoint-1",
                path="/orders",
                method=HttpMethod.GET,
            ),
        ),
    )
    second = ApiContract(
        contract_id="contract-2",
        title="Second API",
        style=ApiStyle.OPENAPI,
        source_path="openapi.yaml",
        endpoints=(
            ApiEndpoint(
                endpoint_id="endpoint-2",
                path="/orders",
                method=HttpMethod.GET,
            ),
        ),
    )

    assert {
        finding.category
        for finding in compatibility_findings(
            (first, second)
        )
    } == {"duplicate_route_contract"}
'@

Write-Utf8NoBom "tests\test_domain_intelligence_api_security.py" @'
from forge.domain_intelligence.api.models import (
    ApiAuthenticationKind,
    ApiContract,
    ApiEndpoint,
    ApiStyle,
    HttpMethod,
)
from forge.domain_intelligence.api.security import (
    security_findings,
)


def test_security_flags_missing_authentication() -> None:
    contract = ApiContract(
        contract_id="contract-1",
        title="ERP API",
        style=ApiStyle.REST,
        source_path="routes.py",
        endpoints=(
            ApiEndpoint(
                endpoint_id="endpoint-1",
                path="/orders",
                method=HttpMethod.GET,
            ),
            ApiEndpoint(
                endpoint_id="endpoint-2",
                path="/secure-orders",
                method=HttpMethod.GET,
                authentication=(
                    ApiAuthenticationKind.BEARER,
                ),
            ),
        ),
    )

    findings = security_findings((contract,))

    assert len(findings) == 1
    assert findings[0].evidence["path"] == "/orders"
'@

Write-Host ""
Write-Host "M4.4 Package 2 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_domain_intelligence_api_graphql.py `
    .\tests\test_domain_intelligence_api_dependencies.py `
    .\tests\test_domain_intelligence_api_versioning.py `
    .\tests\test_domain_intelligence_api_compatibility.py `
    .\tests\test_domain_intelligence_api_security.py `
    -p no:cacheprovider
Assert-CommandSuccess "M4.4 Package 2 tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M4.4 PACKAGE 2 COMPLETE" -ForegroundColor Green

git status --short
