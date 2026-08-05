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

Write-Utf8NoBom "forge\domain_intelligence\business_domain\reporting.py" @'
"""Reporting for M4.5 Business Domain Intelligence."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from forge.domain_intelligence.business_domain.errors import (
    BusinessDomainIntelligenceError,
)
from forge.domain_intelligence.business_domain.models import (
    BusinessDomainAnalysisReport,
)


def business_domain_report_summary(
    report: BusinessDomainAnalysisReport,
) -> dict[str, object]:
    """Return a deterministic business-domain summary."""
    entity_kinds = Counter(
        entity.kind.value for entity in report.entities
    )
    finding_categories = Counter(
        finding.category for finding in report.findings
    )
    rule_severities = Counter(
        rule.severity.value for rule in report.rules
    )

    return {
        "report_id": report.report_id,
        "project_id": report.project.project_id,
        "project_root": report.project.root,
        "domains": [
            domain.value for domain in report.project.domains
        ],
        "modules": list(report.project.modules),
        "source_file_count": len(report.project.source_files),
        "configuration_file_count": len(
            report.project.configuration_files
        ),
        "entity_count": len(report.entities),
        "workflow_count": len(report.workflows),
        "rule_count": len(report.rules),
        "finding_count": len(report.findings),
        "entity_kinds": dict(sorted(entity_kinds.items())),
        "rule_severities": dict(
            sorted(rule_severities.items())
        ),
        "finding_categories": dict(
            sorted(finding_categories.items())
        ),
    }


def render_business_domain_markdown(
    report: BusinessDomainAnalysisReport,
) -> str:
    """Render a stable Markdown business-domain report."""
    summary = business_domain_report_summary(report)

    lines = [
        "# Business Domain Intelligence Report",
        "",
        f"- Report ID: `{report.report_id}`",
        f"- Project ID: `{report.project.project_id}`",
        f"- Project root: `{report.project.root}`",
        (
            "- Domains: "
            + ", ".join(
                domain.value
                for domain in report.project.domains
            )
        ),
        (
            "- Modules: "
            + (
                ", ".join(report.project.modules)
                if report.project.modules
                else "none detected"
            )
        ),
        f"- Entities: `{summary['entity_count']}`",
        f"- Workflows: `{summary['workflow_count']}`",
        f"- Rules: `{summary['rule_count']}`",
        f"- Findings: `{summary['finding_count']}`",
        "",
        "## Entities",
        "",
    ]

    if not report.entities:
        lines.append("No business entities were detected.")
        lines.append("")
    else:
        lines.append("| Name | Kind | Module | Sources |")
        lines.append("|---|---|---|---|")

        for entity in report.entities:
            lines.append(
                "| "
                f"{entity.name} | "
                f"{entity.kind.value} | "
                f"{entity.module or ''} | "
                f"{', '.join(entity.source_paths)} |"
            )

        lines.append("")

    lines.extend(["## Workflows", ""])

    if not report.workflows:
        lines.append("No business workflows were inferred.")
        lines.append("")
    else:
        for workflow in report.workflows:
            lines.extend(
                [
                    f"### {workflow.name}",
                    "",
                    f"- Workflow ID: `{workflow.workflow_id}`",
                    f"- Module: `{workflow.module or ''}`",
                    f"- Steps: `{len(workflow.steps)}`",
                    "",
                ]
            )

            for step in workflow.steps:
                lines.append(
                    f"{step.sequence}. {step.name}"
                )

            lines.append("")

    lines.extend(["## Rules", ""])

    if not report.rules:
        lines.append("No business rules were inferred.")
        lines.append("")
    else:
        for rule in report.rules:
            lines.extend(
                [
                    f"### {rule.name}",
                    "",
                    f"- Rule ID: `{rule.rule_id}`",
                    f"- Severity: `{rule.severity.value}`",
                    f"- Module: `{rule.module or ''}`",
                    f"- Description: {rule.description}",
                    "",
                ]
            )

    lines.extend(["## Findings", ""])

    if not report.findings:
        lines.append("No business-domain findings were produced.")
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


def write_business_domain_report_bundle(
    report: BusinessDomainAnalysisReport,
    destination: Path,
) -> dict[str, Path]:
    """Write JSON, summary JSON, and Markdown reports."""
    try:
        destination.mkdir(parents=True, exist_ok=True)

        raw_json = destination / "BUSINESS_DOMAIN_ANALYSIS.json"
        summary_json = destination / "BUSINESS_DOMAIN_SUMMARY.json"
        markdown = destination / "BUSINESS_DOMAIN_ANALYSIS.md"

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
                business_domain_report_summary(report),
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        markdown.write_text(
            render_business_domain_markdown(report),
            encoding="utf-8",
        )
    except OSError as exc:
        raise BusinessDomainIntelligenceError(
            "unable to write business-domain report bundle"
        ) from exc

    return {
        raw_json.name: raw_json,
        summary_json.name: summary_json,
        markdown.name: markdown,
    }
'@

Write-Utf8NoBom "tests\test_domain_intelligence_business_domain_reporting.py" @'
import json
from pathlib import Path

from forge.domain_intelligence.business_domain.models import (
    BusinessDomainAnalysisReport,
    BusinessDomainFinding,
    BusinessDomainKind,
    BusinessDomainProject,
    BusinessEntity,
    BusinessEntityKind,
    BusinessFindingSeverity,
    BusinessRule,
    BusinessRuleSeverity,
    BusinessWorkflow,
    BusinessWorkflowStep,
)
from forge.domain_intelligence.business_domain.reporting import (
    business_domain_report_summary,
    render_business_domain_markdown,
    write_business_domain_report_bundle,
)


def report_for() -> BusinessDomainAnalysisReport:
    project = BusinessDomainProject(
        project_id="project-1",
        root="apps/erp",
        domains=(BusinessDomainKind.ERP,),
        modules=("procurement",),
        source_files=("procurement/models.py",),
    )
    entity = BusinessEntity(
        entity_id="entity-1",
        name="PurchaseOrder",
        kind=BusinessEntityKind.TRANSACTION,
        module="procurement",
        source_paths=("procurement/models.py",),
    )
    workflow = BusinessWorkflow(
        workflow_id="workflow-1",
        name="Procure To Pay",
        module="procurement",
        steps=(
            BusinessWorkflowStep(
                name="Create Purchase Order",
                sequence=1,
                entity_names=("PurchaseOrder",),
            ),
        ),
    )
    rule = BusinessRule(
        rule_id="rule-1",
        name="Purchase Order Requires Approval",
        description="Purchase orders require approval.",
        severity=BusinessRuleSeverity.HIGH,
        module="procurement",
        entity_names=("PurchaseOrder",),
    )
    finding = BusinessDomainFinding(
        finding_id="finding-1",
        category="erp",
        severity=BusinessFindingSeverity.INFO,
        message="ERP module detected.",
    )

    return BusinessDomainAnalysisReport(
        report_id="report-1",
        project=project,
        entities=(entity,),
        workflows=(workflow,),
        rules=(rule,),
        findings=(finding,),
    )


def test_business_domain_report_summary() -> None:
    summary = business_domain_report_summary(report_for())

    assert summary["entity_count"] == 1
    assert summary["workflow_count"] == 1
    assert summary["rule_count"] == 1
    assert summary["finding_categories"] == {"erp": 1}


def test_business_domain_markdown_contains_sections() -> None:
    rendered = render_business_domain_markdown(report_for())

    assert "Business Domain Intelligence Report" in rendered
    assert "PurchaseOrder" in rendered
    assert "Procure To Pay" in rendered
    assert "Purchase Order Requires Approval" in rendered


def test_business_domain_report_bundle(
    tmp_path: Path,
) -> None:
    written = write_business_domain_report_bundle(
        report_for(),
        tmp_path / "reports",
    )

    assert set(written) == {
        "BUSINESS_DOMAIN_ANALYSIS.json",
        "BUSINESS_DOMAIN_SUMMARY.json",
        "BUSINESS_DOMAIN_ANALYSIS.md",
    }

    summary = json.loads(
        written["BUSINESS_DOMAIN_SUMMARY.json"].read_text(
            encoding="utf-8"
        )
    )
    assert summary["entity_count"] == 1
'@

Write-Utf8NoBom "tests\test_domain_intelligence_business_domain_service.py" @'
from pathlib import Path

from forge.domain_intelligence.business_domain.models import (
    BusinessDomainAnalysisRequest,
    BusinessDomainKind,
)
from forge.domain_intelligence.business_domain.reporting import (
    business_domain_report_summary,
)
from forge.domain_intelligence.business_domain.service import (
    BusinessDomainIntelligenceService,
    default_business_domain_registry,
)


def initialize_repository(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()


def test_default_business_domain_registry() -> None:
    assert default_business_domain_registry().names() == (
        "crm",
        "erp",
    )


def test_service_builds_complete_business_report(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)

    procurement = tmp_path / "procurement"
    procurement.mkdir()

    (procurement / "models.py").write_text(
        """
        class PurchaseOrder:
            pass
        """,
        encoding="utf-8",
    )

    report = BusinessDomainIntelligenceService().analyze(
        BusinessDomainAnalysisRequest(
            repository_root=str(tmp_path),
        )
    )
    summary = business_domain_report_summary(report)

    assert report.project.domains == (
        BusinessDomainKind.ERP,
    )
    assert report.entities
    assert report.workflows
    assert report.rules
    assert summary["entity_count"] == 1
    assert summary["workflow_count"] == 1


def test_service_reports_unknown_domain(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)

    report = BusinessDomainIntelligenceService().analyze(
        BusinessDomainAnalysisRequest(
            repository_root=str(tmp_path),
        )
    )

    assert report.project.domains == (
        BusinessDomainKind.UNKNOWN,
    )
    assert not report.entities
    assert not report.workflows
    assert not report.rules
'@

Write-Host ""
Write-Host "M4.5 Package 3 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_domain_intelligence_business_domain_reporting.py `
    .\tests\test_domain_intelligence_business_domain_service.py `
    -p no:cacheprovider
Assert-CommandSuccess "M4.5 Package 3 tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M4.5 PACKAGE 3 COMPLETE" -ForegroundColor Green

git status --short
