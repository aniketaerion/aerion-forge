from pathlib import Path

import pytest

from forge.domain_intelligence.business_domain.errors import (
    BusinessDomainPolicyError,
)
from forge.domain_intelligence.business_domain.models import (
    BusinessDomainAnalysisRequest,
)
from forge.domain_intelligence.business_domain.policies import (
    BusinessDomainIntelligencePolicy,
    resolve_business_domain_repository_root,
    validate_business_domain_request,
)


def test_business_domain_policy_is_offline_and_read_only() -> None:
    policy = BusinessDomainIntelligencePolicy()

    assert not policy.allow_network
    assert not policy.allow_database_connections
    assert not policy.allow_external_ontology_fetch
    assert not policy.allow_secret_inspection
    assert not policy.allow_mutation


def test_business_domain_repository_requires_git(
    tmp_path: Path,
) -> None:
    with pytest.raises(BusinessDomainPolicyError):
        resolve_business_domain_repository_root(
            tmp_path,
            BusinessDomainIntelligencePolicy(),
        )


def test_business_domain_request_rejects_path_escape() -> None:
    request = BusinessDomainAnalysisRequest(
        repository_root=".",
        project_root="../outside",
    )

    with pytest.raises(BusinessDomainPolicyError):
        validate_business_domain_request(
            request,
            BusinessDomainIntelligencePolicy(),
        )