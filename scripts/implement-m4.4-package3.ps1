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

Write-Utf8NoBom "forge\domain_intelligence\api\contracts.py" @'
"""API contract aggregation for M4.4 API Domain Intelligence."""

from __future__ import annotations

from pathlib import Path

from forge.domain_intelligence.api.graphql import (
    parse_graphql_contract,
)
from forge.domain_intelligence.api.identifiers import (
    api_contract_identifier,
)
from forge.domain_intelligence.api.models import (
    ApiContract,
    ApiStyle,
)
from forge.domain_intelligence.api.openapi import (
    discover_openapi_files,
    parse_openapi_file,
)
from forge.domain_intelligence.api.rest import (
    discover_rest_endpoints,
)


def discover_api_contracts(
    project_root: Path,
) -> tuple[ApiContract, ...]:
    """Discover OpenAPI, REST, and GraphQL contracts."""
    contracts: list[ApiContract] = []

    for relative_path in discover_openapi_files(project_root):
        contracts.append(
            parse_openapi_file(project_root, relative_path)
        )

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

    graphql_contract = parse_graphql_contract(project_root)

    if graphql_contract is not None:
        contracts.append(graphql_contract)

    return tuple(
        sorted(
            contracts,
            key=lambda contract: (
                contract.style.value,
                contract.source_path,
                contract.contract_id,
            ),
        )
    )
'@

Write-Utf8NoBom "forge\domain_intelligence\api\reporting.py" @'
"""Reporting for M4.4 API Domain Intelligence."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from forge.domain_intelligence.api.errors import (
    ApiIntelligenceError,
)
from forge.domain_intelligence.api.models import (
    ApiAnalysisReport,
)


def api_report_summary(
    report: ApiAnalysisReport,
) -> dict[str, object]:
    """Return a deterministic API summary."""
    categories = Counter(
        finding.category for finding in report.findings
    )

    endpoint_count = sum(
        len(contract.endpoints)
        for contract in report.contracts
    )

    authenticated_endpoint_count = sum(
        1
        for contract in report.contracts
        for endpoint in contract.endpoints
        if endpoint.authentication
    )

    return {
        "report_id": report.report_id,
        "project_id": report.project.project_id,
        "project_root": report.project.root,
        "styles": [
            style.value for style in report.project.styles
        ],
        "contract_file_count": len(
            report.project.contract_files
        ),
        "source_file_count": len(
            report.project.source_files
        ),
        "configuration_file_count": len(
            report.project.configuration_files
        ),
        "contract_count": len(report.contracts),
        "endpoint_count": endpoint_count,
        "authenticated_endpoint_count": (
            authenticated_endpoint_count
        ),
        "finding_count": len(report.findings),
        "finding_categories": dict(
            sorted(categories.items())
        ),
    }


def render_api_markdown(
    report: ApiAnalysisReport,
) -> str:
    """Render a stable Markdown API-intelligence report."""
    summary = api_report_summary(report)

    lines = [
        "# API Intelligence Report",
        "",
        f"- Report ID: `{report.report_id}`",
        f"- Project ID: `{report.project.project_id}`",
        f"- Project root: `{report.project.root}`",
        (
            "- Styles: "
            + ", ".join(
                style.value
                for style in report.project.styles
            )
        ),
        f"- Contracts: `{summary['contract_count']}`",
        f"- Endpoints: `{summary['endpoint_count']}`",
        (
            "- Authenticated endpoints: "
            f"`{summary['authenticated_endpoint_count']}`"
        ),
        f"- Findings: `{summary['finding_count']}`",
        "",
        "## API Artifacts",
        "",
        (
            "- Contract files: "
            + (
                ", ".join(report.project.contract_files)
                if report.project.contract_files
                else "none detected"
            )
        ),
        (
            "- Source files: "
            + (
                ", ".join(report.project.source_files)
                if report.project.source_files
                else "none detected"
            )
        ),
        (
            "- Configuration files: "
            + (
                ", ".join(
                    report.project.configuration_files
                )
                if report.project.configuration_files
                else "none detected"
            )
        ),
        "",
        "## Contracts",
        "",
    ]

    if not report.contracts:
        lines.append("No API contracts were detected.")
        lines.append("")
    else:
        for contract in report.contracts:
            lines.extend(
                [
                    f"### {contract.title}",
                    "",
                    f"- Contract ID: `{contract.contract_id}`",
                    f"- Style: `{contract.style.value}`",
                    (
                        f"- Version: `{contract.version}`"
                        if contract.version is not None
                        else "- Version: not declared"
                    ),
                    f"- Source: `{contract.source_path}`",
                    (
                        "- Endpoints: "
                        f"`{len(contract.endpoints)}`"
                    ),
                    "",
                ]
            )

            if contract.endpoints:
                lines.append(
                    "| Method | Path | Operation | Auth |"
                )
                lines.append("|---|---|---|---|")

                for endpoint in contract.endpoints:
                    auth = (
                        ", ".join(
                            item.value
                            for item in endpoint.authentication
                        )
                        if endpoint.authentication
                        else "none detected"
                    )
                    lines.append(
                        "| "
                        f"{endpoint.method.value} | "
                        f"{endpoint.path} | "
                        f"{endpoint.operation_id or ''} | "
                        f"{auth} |"
                    )

                lines.append("")

    lines.extend(
        [
            "## Findings",
            "",
        ]
    )

    if not report.findings:
        lines.append("No API findings were produced.")
    else:
        for finding in report.findings:
            lines.extend(
                [
                    f"### {finding.category}",
                    "",
                    f"- Finding ID: `{finding.finding_id}`",
                    f"- Severity: `{finding.severity.value}`",
                    f"- Message: {finding.message}",
                    (
                        f"- Path: `{finding.path}`"
                        if finding.path is not None
                        else "- Path: not applicable"
                    ),
                ]
            )

            if finding.evidence:
                lines.append("- Evidence:")
                for key, value in sorted(
                    finding.evidence.items()
                ):
                    lines.append(
                        f"  - `{key}`: `{value}`"
                    )

            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def write_api_report_bundle(
    report: ApiAnalysisReport,
    destination: Path,
) -> dict[str, Path]:
    """Write JSON, summary JSON, and Markdown reports."""
    try:
        destination.mkdir(parents=True, exist_ok=True)

        raw_json = destination / "API_ANALYSIS.json"
        summary_json = destination / "API_SUMMARY.json"
        markdown = destination / "API_ANALYSIS.md"

        raw_json.write_text(
            json.dumps(
                report.model_dump(mode="json"),
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        summary_json.write_text(
            json.dumps(
                api_report_summary(report),
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        markdown.write_text(
            render_api_markdown(report),
            encoding="utf-8",
        )
    except OSError as exc:
        raise ApiIntelligenceError(
            f"unable to write API report bundle: {destination}"
        ) from exc

    return {
        raw_json.name: raw_json,
        summary_json.name: summary_json,
        markdown.name: markdown,
    }
'@

Write-Utf8NoBom "forge\domain_intelligence\api\service.py" @'
"""Complete API analysis service for M4.4."""

from __future__ import annotations

from forge.domain_intelligence.api.compatibility import (
    compatibility_findings,
)
from forge.domain_intelligence.api.contracts import (
    discover_api_contracts,
)
from forge.domain_intelligence.api.dependencies import (
    dependency_findings,
    discover_api_dependencies,
)
from forge.domain_intelligence.api.discovery import (
    discover_api_source_files,
    discovery_findings,
)
from forge.domain_intelligence.api.graphql import (
    discover_graphql_files,
    graphql_findings,
)
from forge.domain_intelligence.api.identifiers import (
    api_project_identifier,
    api_report_identifier,
)
from forge.domain_intelligence.api.models import (
    ApiAnalysisReport,
    ApiAnalysisRequest,
    ApiProject,
    ApiStyle,
)
from forge.domain_intelligence.api.openapi import (
    discover_openapi_files,
    openapi_findings,
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
    rest_findings,
)
from forge.domain_intelligence.api.security import (
    security_findings,
)
from forge.domain_intelligence.api.versioning import (
    versioning_findings,
)


def default_api_registry() -> ApiAnalyzerRegistry:
    """Return the complete M4.4 analyzer registry."""
    return ApiAnalyzerRegistry(
        (
            ("dependencies", dependency_findings),
            ("discovery", discovery_findings),
            ("graphql", graphql_findings),
            ("openapi", openapi_findings),
            ("rest", rest_findings),
        )
    )


class ApiIntelligenceService:
    """Discover, analyze, and report API architecture."""

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
        """Run the complete M4.4 API-analysis pipeline."""
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

        contracts = discover_api_contracts(project_root)
        styles = {
            contract.style for contract in contracts
        }
        contract_files = discover_openapi_files(project_root)
        source_files = discover_api_source_files(project_root)
        graphql_files = discover_graphql_files(project_root)
        dependencies = discover_api_dependencies(project_root)

        configuration_files = tuple(
            sorted(
                {
                    *contract_files,
                    *(
                        ("package.json",)
                        if (project_root / "package.json").is_file()
                        else ()
                    ),
                    *(
                        ("requirements.txt",)
                        if (
                            project_root
                            / "requirements.txt"
                        ).is_file()
                        else ()
                    ),
                }
            )
        )

        project_payload = {
            "root": request.project_root,
            "styles": sorted(style.value for style in styles),
            "contract_files": contract_files,
            "source_files": source_files,
            "graphql_files": graphql_files,
            "dependencies": dependencies,
            "configuration_files": configuration_files,
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
            contract_files=contract_files,
            source_files=source_files,
            configuration_files=configuration_files,
        )

        findings = (
            *self.registry.analyze(project_root),
            *versioning_findings(contracts),
            *compatibility_findings(contracts),
            *security_findings(contracts),
        )

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
            contracts=contracts,
            findings=tuple(
                sorted(
                    findings,
                    key=lambda finding: finding.finding_id,
                )
            ),
        )
'@

Write-Utf8NoBom "tests\test_domain_intelligence_api_contracts.py" @'
from pathlib import Path

from forge.domain_intelligence.api.contracts import (
    discover_api_contracts,
)
from forge.domain_intelligence.api.models import ApiStyle


def test_discover_api_contracts_combines_styles(
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
    (tmp_path / "schema.graphql").write_text(
        """
        type Query {
            orders: [String!]!
        }
        """,
        encoding="utf-8",
    )

    contracts = discover_api_contracts(tmp_path)

    assert {
        contract.style for contract in contracts
    } == {
        ApiStyle.GRAPHQL,
        ApiStyle.OPENAPI,
        ApiStyle.REST,
    }
'@

Write-Utf8NoBom "tests\test_domain_intelligence_api_reporting.py" @'
import json
from pathlib import Path

from forge.domain_intelligence.api.models import (
    ApiAnalysisReport,
    ApiContract,
    ApiEndpoint,
    ApiFinding,
    ApiFindingSeverity,
    ApiProject,
    ApiStyle,
    HttpMethod,
)
from forge.domain_intelligence.api.reporting import (
    api_report_summary,
    render_api_markdown,
    write_api_report_bundle,
)


def report_for() -> ApiAnalysisReport:
    project = ApiProject(
        project_id="api-project-1",
        root="apps/api",
        styles=(ApiStyle.REST,),
        source_files=("routes.py",),
    )
    contract = ApiContract(
        contract_id="contract-1",
        title="ERP API",
        version="1.0.0",
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
    finding = ApiFinding(
        finding_id="finding-1",
        category="missing_authentication",
        severity=ApiFindingSeverity.HIGH,
        message="Authentication missing.",
    )

    return ApiAnalysisReport(
        report_id="api-report-1",
        project=project,
        contracts=(contract,),
        findings=(finding,),
    )


def test_api_report_summary() -> None:
    summary = api_report_summary(report_for())

    assert summary["contract_count"] == 1
    assert summary["endpoint_count"] == 1
    assert summary["finding_categories"] == {
        "missing_authentication": 1
    }


def test_api_markdown_contains_endpoint() -> None:
    rendered = render_api_markdown(report_for())

    assert "API Intelligence Report" in rendered
    assert "/orders" in rendered
    assert "routes.py" in rendered


def test_api_report_bundle_writes_files(
    tmp_path: Path,
) -> None:
    written = write_api_report_bundle(
        report_for(),
        tmp_path / "reports",
    )

    assert set(written) == {
        "API_ANALYSIS.json",
        "API_SUMMARY.json",
        "API_ANALYSIS.md",
    }

    summary = json.loads(
        written["API_SUMMARY.json"].read_text(
            encoding="utf-8"
        )
    )
    assert summary["finding_count"] == 1
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


def test_default_api_registry_is_complete() -> None:
    assert default_api_registry().names() == (
        "dependencies",
        "discovery",
        "graphql",
        "openapi",
        "rest",
    )


def test_service_runs_complete_api_pipeline(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)

    (tmp_path / "package.json").write_text(
        """
        {
          "dependencies": {
            "express": "^5.0.0",
            "graphql": "^16.0.0"
          }
        }
        """,
        encoding="utf-8",
    )
    (tmp_path / "openapi.yaml").write_text(
        """
        openapi: 3.0.0
        info:
          title: ERP API
          version: 1.0.0
        paths:
          /v1/orders:
            get:
              operationId: listOrders
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
    (tmp_path / "schema.graphql").write_text(
        """
        type Query {
            orders: [String!]!
        }
        """,
        encoding="utf-8",
    )

    report = ApiIntelligenceService().analyze(
        ApiAnalysisRequest(
            repository_root=str(tmp_path),
        )
    )

    assert report.project.styles == (
        ApiStyle.GRAPHQL,
        ApiStyle.OPENAPI,
        ApiStyle.REST,
    )
    assert len(report.contracts) == 3

    categories = {
        finding.category for finding in report.findings
    }

    assert "dependencies" in categories
    assert "graphql" in categories
    assert "missing_authentication" in categories


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
    assert not report.contracts
'@

Write-Host ""
Write-Host "M4.4 Package 3 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_domain_intelligence_api_contracts.py `
    .\tests\test_domain_intelligence_api_reporting.py `
    .\tests\test_domain_intelligence_api_service.py `
    -p no:cacheprovider
Assert-CommandSuccess "M4.4 Package 3 tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M4.4 PACKAGE 3 COMPLETE" -ForegroundColor Green

git status --short