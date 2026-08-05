from pathlib import Path

from forge.domain_intelligence.business_domain.manifest import (
    business_domain_manifest,
)
from forge.domain_intelligence.business_domain.models import (
    BusinessDomainKind,
)


def test_business_domain_manifest(tmp_path: Path) -> None:
    (tmp_path / "inventory").mkdir()
    (tmp_path / "leads").mkdir()

    manifest = business_domain_manifest(tmp_path)

    assert manifest["domains"] == (
        BusinessDomainKind.CRM,
        BusinessDomainKind.ERP,
    )