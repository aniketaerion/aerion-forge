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