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