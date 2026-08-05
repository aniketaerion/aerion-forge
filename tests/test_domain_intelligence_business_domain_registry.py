from pathlib import Path

import pytest

from forge.domain_intelligence.business_domain.errors import (
    BusinessDomainConfigurationError,
)
from forge.domain_intelligence.business_domain.models import (
    BusinessDomainFinding,
)
from forge.domain_intelligence.business_domain.registry import (
    BusinessDomainAnalyzerRegistry,
)


def empty_analyzer(
    project_root: Path,
) -> tuple[BusinessDomainFinding, ...]:
    del project_root
    return ()


def test_business_domain_registry_names_are_sorted() -> None:
    registry = BusinessDomainAnalyzerRegistry(
        (
            ("erp", empty_analyzer),
            ("crm", empty_analyzer),
        )
    )

    assert registry.names() == ("crm", "erp")


def test_business_domain_registry_rejects_duplicates() -> None:
    with pytest.raises(BusinessDomainConfigurationError):
        BusinessDomainAnalyzerRegistry(
            (
                ("erp", empty_analyzer),
                ("ERP", empty_analyzer),
            )
        )