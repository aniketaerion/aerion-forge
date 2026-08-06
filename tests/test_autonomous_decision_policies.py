import pytest

from forge.autonomous_decision.errors import DecisionPolicyError
from forge.autonomous_decision.policies import (
    AutonomousDecisionPolicy,
    DecisionSafetyPolicy,
    DecisionWeightPolicy,
)


def test_default_policy_is_safe_and_bounded() -> None:
    policy = AutonomousDecisionPolicy()

    assert policy.safety.dry_run_by_default
    assert not policy.safety.allow_tool_execution
    assert policy.thresholds.maximum_candidates == 20


def test_weight_total_must_equal_one() -> None:
    with pytest.raises(DecisionPolicyError):
        DecisionWeightPolicy(
            utility_weight=0.50,
            confidence_weight=0.50,
            evidence_weight=0.50,
            reversibility_weight=0.10,
            risk_weight=0.10,
        )


def test_tool_execution_cannot_be_enabled() -> None:
    with pytest.raises(DecisionPolicyError):
        DecisionSafetyPolicy(
            allow_tool_execution=True,
        )