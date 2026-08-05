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