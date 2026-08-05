from pathlib import Path

import pytest

from forge.mission_orchestration.errors import MissionPolicyViolationError
from forge.mission_orchestration.policies import MissionOrchestrationPolicy


def test_policy_defaults_are_bounded() -> None:
    policy = MissionOrchestrationPolicy()
    assert policy.max_stage_attempts == 3
    assert policy.checkpoint_after_each_stage is True
    assert policy.allow_git_mutation is False
    assert policy.allow_arbitrary_shell is False


def test_policy_rejects_protected_path() -> None:
    with pytest.raises(MissionPolicyViolationError):
        MissionOrchestrationPolicy().validate_paths((".git/config",))


def test_policy_rejects_excess_stage_attempts() -> None:
    with pytest.raises(MissionPolicyViolationError):
        MissionOrchestrationPolicy().validate_stage_attempts(4)


def test_policy_resolves_existing_repository(tmp_path: Path) -> None:
    assert MissionOrchestrationPolicy.resolve_repository(tmp_path) == tmp_path.resolve()