from pathlib import Path

import pytest

from forge.domain_intelligence.backend.errors import BackendPolicyError
from forge.domain_intelligence.backend.models import (
    BackendAnalysisRequest,
)
from forge.domain_intelligence.backend.policies import (
    BackendIntelligencePolicy,
    resolve_backend_repository_root,
    validate_backend_request,
)


def test_backend_policy_is_read_only_by_default() -> None:
    policy = BackendIntelligencePolicy()

    assert not policy.allow_network
    assert not policy.allow_process_execution
    assert not policy.allow_source_modification
    assert not policy.inspect_secrets


def test_backend_repository_requires_git(tmp_path: Path) -> None:
    with pytest.raises(BackendPolicyError):
        resolve_backend_repository_root(
            tmp_path,
            BackendIntelligencePolicy(),
        )


def test_backend_request_rejects_escape() -> None:
    request = BackendAnalysisRequest(
        repository_root=".",
        project_root="../outside",
    )

    with pytest.raises(BackendPolicyError):
        validate_backend_request(
            request,
            BackendIntelligencePolicy(),
        )