import pytest
from pydantic import ValidationError

from forge.domain_intelligence.business_domain.models import (
    BusinessDomainAnalysisReport,
    BusinessDomainFinding,
    BusinessDomainKind,
    BusinessDomainProject,
    BusinessEntity,
    BusinessEntityKind,
    BusinessFindingSeverity,
    BusinessWorkflow,
    BusinessWorkflowStep,
)


def test_business_entity_supports_module_and_attributes() -> None:
    entity = BusinessEntity(
        entity_id="entity-1",
        name="PurchaseOrder",
        kind=BusinessEntityKind.TRANSACTION,
        module="procurement",
        attributes=("supplier_id", "status"),
    )

    assert entity.module == "procurement"


def test_business_workflow_rejects_duplicate_sequences() -> None:
    with pytest.raises(ValidationError):
        BusinessWorkflow(
            workflow_id="workflow-1",
            name="Procure to Pay",
            steps=(
                BusinessWorkflowStep(
                    name="Create Requisition",
                    sequence=1,
                ),
                BusinessWorkflowStep(
                    name="Approve Requisition",
                    sequence=1,
                ),
            ),
        )


def test_business_report_rejects_duplicate_findings() -> None:
    project = BusinessDomainProject(
        project_id="project-1",
        root="apps/erp",
        domains=(BusinessDomainKind.ERP,),
    )
    finding = BusinessDomainFinding(
        finding_id="finding-1",
        category="workflow",
        severity=BusinessFindingSeverity.HIGH,
        message="Broken workflow.",
    )

    with pytest.raises(ValidationError):
        BusinessDomainAnalysisReport(
            report_id="report-1",
            project=project,
            findings=(finding, finding),
        )