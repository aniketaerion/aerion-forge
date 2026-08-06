from forge.autonomous_execution_v2.policies import (
    AutonomousExecutionV2Policy,
)


def test_default_policy_is_safe() -> None:
    policy = AutonomousExecutionV2Policy()

    assert policy.safety.require_approved_plan
    assert policy.safety.require_evidence_for_success
    assert not policy.safety.allow_destructive_execution
    assert policy.limits.maximum_attempts_per_step == 3