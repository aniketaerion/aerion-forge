from forge.mission_runtime.policies import MissionRuntimePolicy


def test_default_mission_policy_is_safe() -> None:
    policy = MissionRuntimePolicy()

    assert policy.safety.require_active_workspace
    assert policy.safety.require_registered_capabilities
    assert policy.safety.require_verification_before_completion
    assert not policy.safety.allow_unrestricted_git_operations
    assert not policy.safety.allow_self_modification
    assert (
        policy.approvals
        .require_plan_approval_for_high_risk
    )