import pytest
from pydantic import ValidationError

from forge.autonomous_orchestration.errors import (
    OrchestrationPolicyError,
)
from forge.autonomous_orchestration.policies import (
    AutonomousOrchestrationPolicy,
    OrchestrationBudgetPolicy,
    OrchestrationSafetyPolicy,
)


def test_default_policy_is_bounded_and_safe() -> None:
    policy = AutonomousOrchestrationPolicy()

    assert policy.safety.dry_run_by_default
    assert policy.safety.one_execution_per_iteration
    assert policy.budgets.maximum_cycles >= (
        policy.budgets.maximum_step_executions
    )


def test_cycles_must_cover_step_executions() -> None:
    with pytest.raises(ValidationError):
        OrchestrationBudgetPolicy(
            maximum_cycles=5,
            maximum_step_executions=10,
        )


def test_unsafe_replay_policy_is_rejected() -> None:
    with pytest.raises(OrchestrationPolicyError):
        OrchestrationSafetyPolicy(
            allow_completed_step_replay=True,
        )