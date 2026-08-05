from pathlib import Path

import pytest

from forge.domain_intelligence.embedded.errors import (
    EmbeddedPolicyError,
)
from forge.domain_intelligence.embedded.models import (
    EmbeddedAnalysisRequest,
)
from forge.domain_intelligence.embedded.policies import (
    EmbeddedIntelligencePolicy,
    resolve_embedded_repository_root,
    validate_embedded_request,
)


def test_embedded_policy_is_offline_and_read_only() -> None:
    policy = EmbeddedIntelligencePolicy()

    assert not policy.allow_network
    assert not policy.allow_device_access
    assert not policy.allow_serial_access
    assert not policy.allow_firmware_flash
    assert not policy.allow_build_execution
    assert not policy.allow_mutation


def test_embedded_repository_requires_git(
    tmp_path: Path,
) -> None:
    with pytest.raises(EmbeddedPolicyError):
        resolve_embedded_repository_root(
            tmp_path,
            EmbeddedIntelligencePolicy(),
        )


def test_embedded_request_rejects_path_escape() -> None:
    request = EmbeddedAnalysisRequest(
        repository_root=".",
        project_root="../outside",
    )

    with pytest.raises(EmbeddedPolicyError):
        validate_embedded_request(
            request,
            EmbeddedIntelligencePolicy(),
        )