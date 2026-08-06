import pytest
from pydantic import ValidationError

from forge.autonomous_execution.errors import ExecutionPolicyError
from forge.autonomous_execution.policies import (
    AutonomousExecutionPolicy,
    ExecutionBudgetPolicy,
    ToolGatewayPolicy,
)


def test_default_execution_policy_is_safe() -> None:
    policy = AutonomousExecutionPolicy()

    assert policy.single_writer_required
    assert policy.one_tool_at_a_time
    assert policy.gateway.dry_run_by_default
    assert not policy.gateway.allow_unrestricted_shell


def test_lease_budget_must_cover_execution_budget() -> None:
    with pytest.raises(ValidationError):
        ExecutionBudgetPolicy(
            maximum_execution_seconds=1000,
            maximum_lease_seconds=900,
        )


def test_unsafe_gateway_policy_is_rejected() -> None:
    with pytest.raises(ExecutionPolicyError):
        ToolGatewayPolicy(
            allow_unrestricted_shell=True,
        )