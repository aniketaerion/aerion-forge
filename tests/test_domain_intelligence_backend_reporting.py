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