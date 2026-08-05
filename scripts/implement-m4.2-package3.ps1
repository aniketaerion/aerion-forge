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

Write-Utf8NoBom "forge\domain_intelligence\backend\reporting.py" @'
"""Reporting for M4.2 Backend Domain Intelligence."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from forge.domain_intelligence.backend.errors import (
    BackendIntelligenceError,
)
from forge.domain_intelligence.backend.models import (
    BackendAnalysisReport,
)


def backend_report_summary(
    report: BackendAnalysisReport,
) -> dict[str, object]:
    """Return a deterministic machine-readable backend summary."""
    categories = Counter(
        finding.category for finding in report.findings
    )

    return {
        "report_id": report.report_id,
        "project_id": report.project.project_id,
        "project_root": report.project.root,
        "runtimes": [
            runtime.value
            for runtime in report.project.runtimes
        ],
        "frameworks": [
            framework.value
            for framework in report.project.frameworks
        ],
        "package_manager": report.project.package_manager,
        "source_directories": list(
            report.project.source_directories
        ),
        "configuration_files": list(
            report.project.configuration_files
        ),
        "service_files": list(
            report.project.service_files
        ),
        "worker_files": list(
            report.project.worker_files
        ),
        "finding_count": len(report.findings),
        "finding_categories": dict(
            sorted(categories.items())
        ),
    }


def render_backend_markdown(
    report: BackendAnalysisReport,
) -> str:
    """Render a stable Markdown backend-intelligence report."""
    lines = [
        "# Backend Intelligence Report",
        "",
        f"- Report ID: `{report.report_id}`",
        f"- Project ID: `{report.project.project_id}`",
        f"- Project root: `{report.project.root}`",
        (
            "- Runtimes: "
            + ", ".join(
                runtime.value
                for runtime in report.project.runtimes
            )
        ),
        (
            "- Frameworks: "
            + ", ".join(
                framework.value
                for framework in report.project.frameworks
            )
        ),
        (
            "- Package manager: "
            + (
                report.project.package_manager
                if report.project.package_manager is not None
                else "unknown"
            )
        ),
        f"- Findings: `{len(report.findings)}`",
        "",
        "## Backend Layout",
        "",
        (
            "- Source directories: "
            + (
                ", ".join(report.project.source_directories)
                if report.project.source_directories
                else "none detected"
            )
        ),
        (
            "- Configuration files: "
            + (
                ", ".join(report.project.configuration_files)
                if report.project.configuration_files
                else "none detected"
            )
        ),
        (
            "- Service files: "
            + (
                ", ".join(report.project.service_files)
                if report.project.service_files
                else "none detected"
            )
        ),
        (
            "- Worker files: "
            + (
                ", ".join(report.project.worker_files)
                if report.project.worker_files
                else "none detected"
            )
        ),
        "",
        "## Findings",
        "",
    ]

    if not report.findings:
        lines.append("No backend findings were produced.")
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


def write_backend_report_bundle(
    report: BackendAnalysisReport,
    destination: Path,
) -> dict[str, Path]:
    """Write backend JSON, summary JSON, and Markdown reports."""
    try:
        destination.mkdir(parents=True, exist_ok=True)

        raw_json = destination / "BACKEND_ANALYSIS.json"
        summary_json = destination / "BACKEND_SUMMARY.json"
        markdown = destination / "BACKEND_ANALYSIS.md"

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
                backend_report_summary(report),
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        markdown.write_text(
            render_backend_markdown(report),
            encoding="utf-8",
        )
    except OSError as exc:
        raise BackendIntelligenceError(
            f"unable to write backend report bundle: {destination}"
        ) from exc

    return {
        raw_json.name: raw_json,
        summary_json.name: summary_json,
        markdown.name: markdown,
    }
'@

Write-Utf8NoBom "tests\test_domain_intelligence_backend_reporting.py" @'
import json
from pathlib import Path

from forge.domain_intelligence.backend.models import (
    BackendAnalysisReport,
    BackendFinding,
    BackendFindingSeverity,
    BackendFramework,
    BackendProject,
    BackendRuntime,
)
from forge.domain_intelligence.backend.reporting import (
    backend_report_summary,
    render_backend_markdown,
    write_backend_report_bundle,
)


def report_for() -> BackendAnalysisReport:
    project = BackendProject(
        project_id="backend-project-1",
        root="apps/api",
        runtimes=(BackendRuntime.NODEJS,),
        frameworks=(
            BackendFramework.NODE,
            BackendFramework.EXPRESS,
        ),
        package_manager="npm",
        source_directories=("src",),
        configuration_files=("package.json",),
        service_files=("src/orders_service.ts",),
        worker_files=("src/invoice_worker.ts",),
    )
    finding = BackendFinding(
        finding_id="backend-finding-1",
        category="services",
        severity=BackendFindingSeverity.INFO,
        message="Backend services detected.",
        evidence={"service_file_count": "1"},
    )
    return BackendAnalysisReport(
        report_id="backend-report-1",
        project=project,
        findings=(finding,),
    )


def test_backend_report_summary() -> None:
    summary = backend_report_summary(report_for())

    assert summary["frameworks"] == ["node", "express"]
    assert summary["finding_categories"] == {
        "services": 1
    }


def test_backend_markdown_contains_layout() -> None:
    rendered = render_backend_markdown(report_for())

    assert "Backend Intelligence Report" in rendered
    assert "src/orders_service.ts" in rendered
    assert "src/invoice_worker.ts" in rendered


def test_backend_report_bundle_writes_files(
    tmp_path: Path,
) -> None:
    written = write_backend_report_bundle(
        report_for(),
        tmp_path / "reports",
    )

    assert set(written) == {
        "BACKEND_ANALYSIS.json",
        "BACKEND_SUMMARY.json",
        "BACKEND_ANALYSIS.md",
    }

    summary = json.loads(
        written["BACKEND_SUMMARY.json"].read_text(
            encoding="utf-8"
        )
    )
    assert summary["finding_count"] == 1
'@

Write-Utf8NoBom "forge\domain_intelligence\backend\service.py" @'
"""Complete backend analysis service for M4.2."""

from __future__ import annotations

from forge.domain_intelligence.backend.architecture import (
    architecture_findings,
)
from forge.domain_intelligence.backend.configuration import (
    configuration_findings,
    discover_configuration_files,
)
from forge.domain_intelligence.backend.dependencies import (
    dependency_findings,
)
from forge.domain_intelligence.backend.django import (
    detect_django,
    django_findings,
)
from forge.domain_intelligence.backend.fastapi import (
    detect_fastapi,
    fastapi_findings,
)
from forge.domain_intelligence.backend.identifiers import (
    backend_project_identifier,
    backend_report_identifier,
)
from forge.domain_intelligence.backend.models import (
    BackendAnalysisReport,
    BackendAnalysisRequest,
    BackendFramework,
    BackendProject,
    BackendRuntime,
)
from forge.domain_intelligence.backend.node import (
    detect_node_frameworks,
    detect_node_runtime,
    load_package_json,
    node_findings,
)
from forge.domain_intelligence.backend.policies import (
    BackendIntelligencePolicy,
    resolve_backend_repository_root,
    validate_backend_request,
)
from forge.domain_intelligence.backend.registry import (
    BackendAnalyzerRegistry,
)
from forge.domain_intelligence.backend.services import (
    discover_service_files,
    service_findings,
)
from forge.domain_intelligence.backend.workers import (
    discover_worker_files,
    worker_findings,
)


def default_backend_registry() -> BackendAnalyzerRegistry:
    """Return the complete M4.2 backend analyzer registry."""
    return BackendAnalyzerRegistry(
        (
            ("architecture", architecture_findings),
            ("configuration", configuration_findings),
            ("dependencies", dependency_findings),
            ("django", django_findings),
            ("fastapi", fastapi_findings),
            ("node", node_findings),
            ("services", service_findings),
            ("workers", worker_findings),
        )
    )


class BackendIntelligenceService:
    """Discover, classify, and report backend architecture."""

    def __init__(
        self,
        policy: BackendIntelligencePolicy | None = None,
        registry: BackendAnalyzerRegistry | None = None,
    ) -> None:
        self.policy = policy or BackendIntelligencePolicy()
        self.registry = registry or default_backend_registry()

    def analyze(
        self,
        request: BackendAnalysisRequest,
    ) -> BackendAnalysisReport:
        """Run the complete M4.2 backend-analysis pipeline."""
        validate_backend_request(request, self.policy)

        repository_root = resolve_backend_repository_root(
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
                "resolved backend project root escaped repository"
            ) from exc

        runtimes: set[BackendRuntime] = set(
            detect_node_runtime(project_root)
        )
        frameworks: set[BackendFramework] = set(
            detect_node_frameworks(project_root)
        )

        if detect_fastapi(project_root):
            runtimes.add(BackendRuntime.PYTHON)
            frameworks.add(BackendFramework.FASTAPI)

        if detect_django(project_root):
            runtimes.add(BackendRuntime.PYTHON)
            frameworks.add(BackendFramework.DJANGO)

        package_manager: str | None = None

        if (project_root / "pnpm-lock.yaml").is_file():
            package_manager = "pnpm"
        elif (project_root / "yarn.lock").is_file():
            package_manager = "yarn"
        elif (project_root / "package-lock.json").is_file():
            package_manager = "npm"
        elif (project_root / "poetry.lock").is_file():
            package_manager = "poetry"
        elif (project_root / "Pipfile").is_file():
            package_manager = "pipenv"
        elif (project_root / "requirements.txt").is_file():
            package_manager = "pip"

        package_json = load_package_json(project_root)

        if (
            package_manager is None
            and isinstance(
                package_json.get("packageManager"),
                str,
            )
        ):
            value = str(package_json["packageManager"])
            package_manager = value.split("@", maxsplit=1)[0]

        source_directories = tuple(
            name
            for name in (
                "src",
                "app",
                "apps",
                "server",
                "api",
                "backend",
            )
            if (project_root / name).is_dir()
        )

        configuration_files = discover_configuration_files(
            project_root
        )
        service_files = discover_service_files(project_root)
        worker_files = discover_worker_files(project_root)
        findings = self.registry.analyze(project_root)

        project_payload = {
            "root": request.project_root,
            "runtimes": sorted(
                runtime.value for runtime in runtimes
            ),
            "frameworks": sorted(
                framework.value for framework in frameworks
            ),
            "package_manager": package_manager,
            "configuration_files": configuration_files,
            "service_files": service_files,
            "worker_files": worker_files,
        }

        project = BackendProject(
            project_id=backend_project_identifier(
                project_payload
            ),
            root=request.project_root,
            runtimes=tuple(
                sorted(
                    runtimes,
                    key=lambda runtime: runtime.value,
                )
            )
            or (BackendRuntime.UNKNOWN,),
            frameworks=tuple(
                sorted(
                    frameworks,
                    key=lambda framework: framework.value,
                )
            )
            or (BackendFramework.UNKNOWN,),
            package_manager=package_manager,
            source_directories=source_directories,
            configuration_files=configuration_files,
            service_files=service_files,
            worker_files=worker_files,
        )

        return BackendAnalysisReport(
            report_id=backend_report_identifier(
                {
                    "project_id": project.project_id,
                    "finding_ids": [
                        finding.finding_id
                        for finding in findings
                    ],
                }
            ),
            project=project,
            findings=findings,
        )
'@

Write-Utf8NoBom "tests\test_domain_intelligence_backend_service.py" @'
import json
from pathlib import Path

from forge.domain_intelligence.backend.models import (
    BackendAnalysisRequest,
    BackendFramework,
    BackendRuntime,
)
from forge.domain_intelligence.backend.service import (
    BackendIntelligenceService,
    default_backend_registry,
)


def initialize_repository(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()


def test_default_backend_registry_is_complete() -> None:
    assert default_backend_registry().names() == (
        "architecture",
        "configuration",
        "dependencies",
        "django",
        "fastapi",
        "node",
        "services",
        "workers",
    )


def test_service_runs_complete_backend_pipeline(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)

    source = tmp_path / "src"
    services = source / "services"
    workers = source / "workers"
    services.mkdir(parents=True)
    workers.mkdir(parents=True)

    (tmp_path / "package.json").write_text(
        json.dumps(
            {
                "dependencies": {
                    "express": "^5.0.0",
                }
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "package-lock.json").write_text(
        "{}",
        encoding="utf-8",
    )
    (tmp_path / "requirements.txt").write_text(
        "fastapi==0.116.0\nredis>=6\n",
        encoding="utf-8",
    )
    (services / "orders_service.ts").write_text(
        "export const ordersService = {}",
        encoding="utf-8",
    )
    (workers / "invoice_worker.ts").write_text(
        "export const invoiceWorker = {}",
        encoding="utf-8",
    )

    report = BackendIntelligenceService().analyze(
        BackendAnalysisRequest(
            repository_root=str(tmp_path),
        )
    )

    assert report.project.runtimes == (
        BackendRuntime.NODEJS,
        BackendRuntime.PYTHON,
    )
    assert report.project.frameworks == (
        BackendFramework.EXPRESS,
        BackendFramework.FASTAPI,
        BackendFramework.NODE,
    )
    assert report.project.package_manager == "npm"
    assert report.project.service_files == (
        "src/services/orders_service.ts",
    )
    assert report.project.worker_files == (
        "src/workers/invoice_worker.ts",
    )

    categories = {
        finding.category
        for finding in report.findings
    }
    assert {
        "architecture",
        "configuration",
        "dependencies",
        "framework",
        "services",
        "workers",
    }.issubset(categories)


def test_service_reports_unknown_backend(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)

    report = BackendIntelligenceService().analyze(
        BackendAnalysisRequest(
            repository_root=str(tmp_path),
        )
    )

    assert report.project.runtimes == (
        BackendRuntime.UNKNOWN,
    )
    assert report.project.frameworks == (
        BackendFramework.UNKNOWN,
    )
'@

Write-Host ""
Write-Host "M4.2 Package 3 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_domain_intelligence_backend_reporting.py `
    .\tests\test_domain_intelligence_backend_service.py `
    -p no:cacheprovider
Assert-CommandSuccess "M4.2 Package 3 tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M4.2 PACKAGE 3 COMPLETE" -ForegroundColor Green

git status --short
