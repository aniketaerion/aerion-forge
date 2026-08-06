import pytest
from pydantic import ValidationError

from forge.autonomous_runtime.errors import MissionPolicyError
from forge.autonomous_runtime.policies import (
    AuthorityPolicy,
    AutonomousRuntimePolicy,
    RuntimeBudgetPolicy,
)
from forge.autonomous_runtime.states import AuthorityLevel


def test_default_runtime_policy_is_bounded_and_safe() -> None:
    policy = AutonomousRuntimePolicy()

    assert policy.budgets.maximum_attempts_per_step == 2
    assert policy.budgets.maximum_replans == 2
    assert not policy.network_access_allowed
    assert not policy.unrestricted_mutation_allowed
    assert policy.single_writer_required


def test_execution_cycles_must_cover_steps() -> None:
    with pytest.raises(ValidationError):
        RuntimeBudgetPolicy(
            maximum_steps=50,
            maximum_execution_cycles=20,
        )


def test_autonomous_ceiling_must_be_below_approval_boundary() -> None:
    with pytest.raises(ValidationError):
        AuthorityPolicy(
            autonomous_ceiling=AuthorityLevel.A4_COMMIT,
            explicit_approval_from=AuthorityLevel.A4_COMMIT,
        )


def test_unsafe_runtime_policy_is_rejected() -> None:
    with pytest.raises(MissionPolicyError):
        AutonomousRuntimePolicy(
            unrestricted_mutation_allowed=True,
        )