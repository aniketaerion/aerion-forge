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

Write-Utf8NoBom "forge\domain_intelligence\frontend\reporting.py" @'
"""Reporting for M4.1 Frontend Intelligence."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from forge.domain_intelligence.errors import FrontendAnalysisError
from forge.domain_intelligence.models import FrontendAnalysisReport


def report_summary(
    report: FrontendAnalysisReport,
) -> dict[str, object]:
    """Return a deterministic machine-readable report summary."""
    categories = Counter(
        finding.category for finding in report.findings
    )

    return {
        "report_id": report.report_id,
        "project_id": report.project.project_id,
        "project_root": report.project.root,
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
        "finding_count": len(report.findings),
        "finding_categories": dict(
            sorted(categories.items())
        ),
    }


def render_markdown(
    report: FrontendAnalysisReport,
) -> str:
    """Render a stable Markdown frontend-intelligence report."""
    summary = report_summary(report)

    lines = [
        "# Frontend Intelligence Report",
        "",
        f"- Report ID: `{report.report_id}`",
        f"- Project ID: `{report.project.project_id}`",
        f"- Project root: `{report.project.root}`",
        (
            "- Frameworks: "
            + ", ".join(summary["frameworks"])
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
        "## Source Layout",
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
                ", ".join(
                    report.project.configuration_files
                )
                if report.project.configuration_files
                else "none detected"
            )
        ),
        "",
        "## Findings",
        "",
    ]

    if not report.findings:
        lines.append("No frontend findings were produced.")
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


def write_report_bundle(
    report: FrontendAnalysisReport,
    destination: Path,
) -> dict[str, Path]:
    """Write JSON, summary JSON, and Markdown reports."""
    try:
        destination.mkdir(parents=True, exist_ok=True)

        raw_json = destination / "FRONTEND_ANALYSIS.json"
        summary_json = destination / "FRONTEND_SUMMARY.json"
        markdown = destination / "FRONTEND_ANALYSIS.md"

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
                report_summary(report),
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        markdown.write_text(
            render_markdown(report),
            encoding="utf-8",
        )
    except OSError as exc:
        raise FrontendAnalysisError(
            f"unable to write frontend report bundle: {destination}"
        ) from exc

    return {
        raw_json.name: raw_json,
        summary_json.name: summary_json,
        markdown.name: markdown,
    }
'@

Write-Utf8NoBom "forge\domain_intelligence\frontend\service.py" @'
"""Frontend project analysis service for M4.1."""

from __future__ import annotations

from pathlib import Path

from forge.domain_intelligence.frontend.components import (
    component_findings,
)
from forge.domain_intelligence.frontend.hooks import (
    hook_findings,
)
from forge.domain_intelligence.frontend.nextjs import (
    detect_nextjs,
    nextjs_findings,
)
from forge.domain_intelligence.frontend.react import (
    detect_react,
    load_package_json,
    react_findings,
)
from forge.domain_intelligence.frontend.registry import (
    FrontendAnalyzerRegistry,
)
from forge.domain_intelligence.frontend.routing import (
    route_findings,
)
from forge.domain_intelligence.frontend.state_management import (
    state_management_findings,
)
from forge.domain_intelligence.frontend.styling import (
    styling_findings,
)
from forge.domain_intelligence.frontend.vite import (
    detect_vite,
    vite_findings,
)
from forge.domain_intelligence.identifiers import (
    frontend_project_identifier,
    frontend_report_identifier,
)
from forge.domain_intelligence.models import (
    FrontendAnalysisReport,
    FrontendAnalysisRequest,
    FrontendFramework,
    FrontendProject,
)
from forge.domain_intelligence.policies import (
    DomainIntelligencePolicy,
    resolve_repository_root,
    validate_frontend_request,
)


def default_frontend_registry() -> FrontendAnalyzerRegistry:
    """Return the complete M4.1 analyzer registry."""
    return FrontendAnalyzerRegistry(
        (
            ("components", component_findings),
            ("hooks", hook_findings),
            ("nextjs", nextjs_findings),
            ("react", react_findings),
            ("routing", route_findings),
            (
                "state-management",
                state_management_findings,
            ),
            ("styling", styling_findings),
            ("vite", vite_findings),
        )
    )


class FrontendIntelligenceService:
    """Discover, classify, analyze, and report frontend projects."""

    def __init__(
        self,
        policy: DomainIntelligencePolicy | None = None,
        registry: FrontendAnalyzerRegistry | None = None,
    ) -> None:
        self.policy = policy or DomainIntelligencePolicy()
        self.registry = registry or default_frontend_registry()

    def resolve_project_root(
        self,
        request: FrontendAnalysisRequest,
    ) -> tuple[Path, Path]:
        """Resolve repository and project roots safely."""
        validate_frontend_request(request, self.policy)

        repository_root = resolve_repository_root(
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
                "resolved frontend project root escaped repository"
            ) from exc

        return repository_root, project_root

    def analyze(
        self,
        request: FrontendAnalysisRequest,
    ) -> FrontendAnalysisReport:
        """Run the complete M4.1 frontend-analysis pipeline."""
        _, project_root = self.resolve_project_root(request)

        package_json = load_package_json(project_root)
        frameworks = {
            *detect_react(project_root),
            *detect_vite(project_root),
            *detect_nextjs(project_root),
        }

        package_manager: str | None = None

        if (project_root / "pnpm-lock.yaml").is_file():
            package_manager = "pnpm"
        elif (project_root / "yarn.lock").is_file():
            package_manager = "yarn"
        elif (project_root / "package-lock.json").is_file():
            package_manager = "npm"
        elif "packageManager" in package_json:
            value = package_json["packageManager"]
            if isinstance(value, str):
                package_manager = value.split("@", maxsplit=1)[0]

        configuration_names = (
            "package.json",
            "vite.config.js",
            "vite.config.ts",
            "next.config.js",
            "next.config.mjs",
            "next.config.ts",
            "tsconfig.json",
            "jsconfig.json",
            "tailwind.config.js",
            "tailwind.config.ts",
        )
        configuration_files = tuple(
            name
            for name in configuration_names
            if (project_root / name).is_file()
        )

        source_directories = tuple(
            name
            for name in (
                "src",
                "app",
                "pages",
                "components",
            )
            if (project_root / name).is_dir()
        )

        findings = self.registry.analyze(project_root)

        route_files = tuple(
            sorted(
                {
                    finding.path
                    for finding in findings
                    if finding.category == "routing"
                    and finding.path is not None
                }
            )
        )

        component_files = tuple(
            sorted(
                {
                    finding.path
                    for finding in findings
                    if finding.category == "component"
                    and finding.path is not None
                }
            )
        )

        project_payload = {
            "root": request.project_root,
            "frameworks": sorted(
                framework.value for framework in frameworks
            ),
            "package_manager": package_manager,
            "source_directories": source_directories,
            "configuration_files": configuration_files,
            "route_files": route_files,
            "component_files": component_files,
        }

        project = FrontendProject(
            project_id=frontend_project_identifier(project_payload),
            root=request.project_root,
            frameworks=tuple(
                sorted(
                    frameworks,
                    key=lambda framework: framework.value,
                )
            )
            or (FrontendFramework.UNKNOWN,),
            package_manager=package_manager,
            source_directories=source_directories,
            route_files=route_files,
            component_files=component_files,
            configuration_files=configuration_files,
        )

        return FrontendAnalysisReport(
            report_id=frontend_report_identifier(
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

Write-Utf8NoBom "tests\test_domain_intelligence_frontend_reporting.py" @'
import json
from pathlib import Path

from forge.domain_intelligence.frontend.reporting import (
    render_markdown,
    report_summary,
    write_report_bundle,
)
from forge.domain_intelligence.models import (
    FrontendAnalysisReport,
    FrontendFinding,
    FrontendFindingSeverity,
    FrontendFramework,
    FrontendProject,
)


def report_for() -> FrontendAnalysisReport:
    project = FrontendProject(
        project_id="project-1",
        root="apps/erp",
        frameworks=(
            FrontendFramework.REACT,
            FrontendFramework.VITE,
        ),
        package_manager="npm",
        source_directories=("src",),
        component_files=("src/App.tsx",),
        configuration_files=(
            "package.json",
            "vite.config.ts",
        ),
    )
    finding = FrontendFinding(
        finding_id="finding-1",
        category="component",
        severity=FrontendFindingSeverity.INFO,
        message="Component detected.",
        path="src/App.tsx",
        evidence={"components": "App"},
    )
    return FrontendAnalysisReport(
        report_id="report-1",
        project=project,
        findings=(finding,),
    )


def test_report_summary_is_deterministic() -> None:
    summary = report_summary(report_for())

    assert summary["frameworks"] == ["react", "vite"]
    assert summary["finding_categories"] == {
        "component": 1
    }


def test_markdown_contains_project_and_finding() -> None:
    rendered = render_markdown(report_for())

    assert "Frontend Intelligence Report" in rendered
    assert "apps/erp" in rendered
    assert "src/App.tsx" in rendered


def test_report_bundle_writes_all_files(
    tmp_path: Path,
) -> None:
    written = write_report_bundle(
        report_for(),
        tmp_path / "reports",
    )

    assert set(written) == {
        "FRONTEND_ANALYSIS.json",
        "FRONTEND_SUMMARY.json",
        "FRONTEND_ANALYSIS.md",
    }

    summary = json.loads(
        written["FRONTEND_SUMMARY.json"].read_text(
            encoding="utf-8"
        )
    )
    assert summary["finding_count"] == 1
'@

Write-Utf8NoBom "tests\test_domain_intelligence_frontend_service.py" @'
import json
from pathlib import Path

from forge.domain_intelligence.frontend.service import (
    FrontendIntelligenceService,
    default_frontend_registry,
)
from forge.domain_intelligence.models import (
    FrontendAnalysisRequest,
    FrontendFramework,
)


def initialize_repository(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()


def test_default_registry_contains_all_m41_analyzers() -> None:
    assert default_frontend_registry().names() == (
        "components",
        "hooks",
        "nextjs",
        "react",
        "routing",
        "state-management",
        "styling",
        "vite",
    )


def test_service_runs_complete_frontend_pipeline(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)
    source = tmp_path / "src"
    source.mkdir()

    (tmp_path / "package-lock.json").write_text(
        "{}",
        encoding="utf-8",
    )
    (tmp_path / "package.json").write_text(
        json.dumps(
            {
                "dependencies": {
                    "react": "^19.0.0",
                    "zustand": "^5.0.0",
                },
                "devDependencies": {
                    "vite": "^7.0.0",
                    "tailwindcss": "^4.0.0",
                },
            }
        ),
        encoding="utf-8",
    )
    (source / "App.tsx").write_text(
        """
        export function App() {
            const mission = useMission()
            return <Route path="/missions" element={<div />} />
        }
        """,
        encoding="utf-8",
    )
    (source / "app.css").write_text(
        ".root {}",
        encoding="utf-8",
    )

    report = FrontendIntelligenceService().analyze(
        FrontendAnalysisRequest(
            repository_root=str(tmp_path),
        )
    )

    assert report.project.frameworks == (
        FrontendFramework.REACT,
        FrontendFramework.VITE,
    )
    assert report.project.package_manager == "npm"
    assert report.project.component_files == ("src/App.tsx",)
    assert report.project.route_files == ("src/App.tsx",)

    categories = {
        finding.category
        for finding in report.findings
    }
    assert {
        "build_tool",
        "component",
        "framework",
        "hooks",
        "routing",
        "state_management",
        "styling",
    }.issubset(categories)


def test_service_reports_unknown_project(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)

    report = FrontendIntelligenceService().analyze(
        FrontendAnalysisRequest(
            repository_root=str(tmp_path),
        )
    )

    assert report.project.frameworks == (
        FrontendFramework.UNKNOWN,
    )
    assert not report.findings
'@

Write-Host ""
Write-Host "M4.1 Package 3 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_domain_intelligence_frontend_reporting.py `
    .\tests\test_domain_intelligence_frontend_service.py `
    -p no:cacheprovider
Assert-CommandSuccess "M4.1 Package 3 tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M4.1 PACKAGE 3 COMPLETE" -ForegroundColor Green

git status --short