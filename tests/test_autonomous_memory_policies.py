import pytest

from forge.autonomous_memory.errors import MemoryPolicyError
from forge.autonomous_memory.policies import (
    AutonomousMemoryPolicy,
    MemorySafetyPolicy,
)


def test_default_policy_is_safe_and_bounded() -> None:
    policy = AutonomousMemoryPolicy()

    assert policy.safety.require_provenance
    assert policy.safety.reject_secrets
    assert not policy.safety.allow_tool_execution
    assert policy.limits.maximum_query_results == 20


def test_tool_execution_cannot_be_enabled() -> None:
    with pytest.raises(MemoryPolicyError):
        MemorySafetyPolicy(allow_tool_execution=True)


def test_repository_evidence_must_win() -> None:
    with pytest.raises(MemoryPolicyError):
        MemorySafetyPolicy(
            current_repository_evidence_wins=False
        )