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