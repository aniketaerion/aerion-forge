from pathlib import Path

from forge.domain_intelligence.business_domain.models import (
    BusinessDomainAnalysisRequest,
    BusinessDomainKind,
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


def test_service_discovers_erp_and_crm(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)

    inventory = tmp_path / "inventory"
    inventory.mkdir()
    leads = tmp_path / "leads"
    leads.mkdir()

    (inventory / "models.py").write_text(
        "class Product:\n    pass\n",
        encoding="utf-8",
    )
    (leads / "models.py").write_text(
        "class Lead:\n    pass\n",
        encoding="utf-8",
    )

    report = BusinessDomainIntelligenceService().analyze(
        BusinessDomainAnalysisRequest(
            repository_root=str(tmp_path),
        )
    )

    assert report.project.domains == (
        BusinessDomainKind.CRM,
        BusinessDomainKind.ERP,
    )
    assert len(report.entities) == 2


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