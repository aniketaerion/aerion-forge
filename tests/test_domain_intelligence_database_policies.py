from pathlib import Path

import pytest

from forge.domain_intelligence.database.errors import DatabasePolicyError
from forge.domain_intelligence.database.models import (
    DatabaseAnalysisRequest,
)
from forge.domain_intelligence.database.policies import (
    DatabaseIntelligencePolicy,
    resolve_database_repository_root,
    validate_database_request,
)


def test_database_policy_is_offline_and_read_only() -> None:
    policy = DatabaseIntelligencePolicy()

    assert not policy.allow_network
    assert not policy.allow_database_connections
    assert not policy.allow_query_execution
    assert not policy.allow_schema_modification
    assert not policy.inspect_secrets


def test_database_repository_requires_git(tmp_path: Path) -> None:
    with pytest.raises(DatabasePolicyError):
        resolve_database_repository_root(
            tmp_path,
            DatabaseIntelligencePolicy(),
        )


def test_database_request_rejects_path_escape() -> None:
    request = DatabaseAnalysisRequest(
        repository_root=".",
        project_root="../outside",
    )

    with pytest.raises(DatabasePolicyError):
        validate_database_request(
            request,
            DatabaseIntelligencePolicy(),
        )