from pathlib import Path

from forge.domain_intelligence.business_domain.models import (
    BusinessDomainAnalysisRequest,
)
from forge.domain_intelligence.business_domain.plugin import (
    business_domain_plugin,
)


def test_business_domain_plugin_analyzes_repository(
    tmp_path: Path,
) -> None:
    (tmp_path / ".git").mkdir()

    plugin = business_domain_plugin()
    report = plugin.analyze(
        BusinessDomainAnalysisRequest(
            repository_root=str(tmp_path),
        )
    )

    assert plugin.name == "business-domain"
    assert report.project.root == "."