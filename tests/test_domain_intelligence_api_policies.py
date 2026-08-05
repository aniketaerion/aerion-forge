from pathlib import Path

import pytest

from forge.domain_intelligence.api.errors import ApiPolicyError
from forge.domain_intelligence.api.models import ApiAnalysisRequest
from forge.domain_intelligence.api.policies import (
    ApiIntelligencePolicy,
    resolve_api_repository_root,
    validate_api_request,
)


def test_api_policy_is_offline_and_read_only() -> None:
    policy = ApiIntelligencePolicy()

    assert not policy.allow_network
    assert not policy.allow_remote_schema_fetch
    assert not policy.allow_request_execution
    assert not policy.allow_secret_inspection
    assert not policy.allow_mutation


def test_api_repository_requires_git(tmp_path: Path) -> None:
    with pytest.raises(ApiPolicyError):
        resolve_api_repository_root(
            tmp_path,
            ApiIntelligencePolicy(),
        )


def test_api_request_rejects_path_escape() -> None:
    request = ApiAnalysisRequest(
        repository_root=".",
        project_root="../outside",
    )

    with pytest.raises(ApiPolicyError):
        validate_api_request(
            request,
            ApiIntelligencePolicy(),
        )