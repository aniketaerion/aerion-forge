from pathlib import Path

import pytest

from forge.domain_intelligence.phase_validation.errors import (
    PhaseValidationPolicyError,
)
from forge.domain_intelligence.phase_validation.models import (
    PhaseValidationRequest,
)
from forge.domain_intelligence.phase_validation.policies import (
    PhaseValidationPolicy,
    resolve_phase_repository_root,
    validate_phase_request,
)


def test_phase_validation_policy_is_offline_read_only() -> None:
    policy = PhaseValidationPolicy()

    assert not policy.allow_network
    assert not policy.allow_repository_mutation
    assert not policy.allow_destructive_commands


def test_phase_repository_requires_git(tmp_path: Path) -> None:
    with pytest.raises(PhaseValidationPolicyError):
        resolve_phase_repository_root(
            tmp_path,
            PhaseValidationPolicy(),
        )


def test_phase_request_cannot_disable_clean_worktree() -> None:
    request = PhaseValidationRequest(
        repository_root=".",
        phase="4",
        require_clean_worktree=False,
    )

    with pytest.raises(PhaseValidationPolicyError):
        validate_phase_request(
            request,
            PhaseValidationPolicy(),
        )