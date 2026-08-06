from forge.autonomous_runtime.models import (
    AutonomousMission,
    MissionCheckpoint,
    MissionRequest,
)
from forge.autonomous_runtime.recovery import (
    RecoveryContext,
    choose_recovery_action,
)
from forge.autonomous_runtime.states import (
    AuthorityLevel,
    RecoveryAction,
)


def mission() -> AutonomousMission:
    return AutonomousMission(
        mission_id="mission-1",
        request=MissionRequest(
            request_id="request-1",
            objective="Recover safely.",
            repository_root="repository",
            requested_authority=AuthorityLevel.A2_MODIFY,
            requested_by="Aerion",
        ),
        granted_authority=AuthorityLevel.A2_MODIFY,
    )


def checkpoint() -> MissionCheckpoint:
    return MissionCheckpoint(
        checkpoint_id="checkpoint-1",
        mission_id="mission-1",
        step_id="step-1",
        kind="git_stash",
        repository_fingerprint="fingerprint-1",
        working_tree_digest="tree-1",
        verified=True,
    )


def test_retryable_failure_uses_retry_budget_first() -> None:
    result = choose_recovery_action(
        mission(),
        RecoveryContext(
            failure_class="transient_tool_failure",
            step_attempt_number=1,
            rollback_attempt_number=0,
            retryable=True,
            checkpoint=checkpoint(),
        ),
    )

    assert result.action is RecoveryAction.RETRY_STEP


def test_fatal_failure_escalates() -> None:
    result = choose_recovery_action(
        mission(),
        RecoveryContext(
            failure_class="rollback_failure",
            step_attempt_number=2,
            rollback_attempt_number=1,
            retryable=False,
        ),
    )

    assert result.action is RecoveryAction.ESCALATE