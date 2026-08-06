from forge.autonomous_planning.policies import AutonomousPlanningPolicy


def test_default_policy_is_safe() -> None:
    policy = AutonomousPlanningPolicy()
    assert policy.safety.require_repository_scope
    assert policy.safety.require_validation_step
    assert not policy.safety.allow_destructive_steps
    assert policy.limits.maximum_steps == 50