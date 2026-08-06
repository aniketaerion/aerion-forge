from forge.autonomous_runtime.models import (
    AutonomousMission,
    MissionCheckpoint,
    MissionRequest,
)
from forge.autonomous_runtime.recovery_service import (
    AutonomousRecoveryService,
    RecoveryRequest,
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


def test_service_validates_checkpoint_and_selects_rollback() -> None:
    checkpoint = MissionCheckpoint(
        checkpoint_id="checkpoint-1",
        mission_id="mission-1",
        step_id="step-1",
        kind="git_stash",
        repository_fingerprint="fingerprint-1",
        working_tree_digest="tree-1",
        verified=True,
    )

    result = AutonomousRecoveryService().evaluate(
        mission(),
        RecoveryRequest(
            failure_class="validation_failure",
            step_attempt_number=2,
            rollback_attempt_number=0,
            retryable=False,
            checkpoint=checkpoint,
            expected_step_id="step-1",
            expected_repository_fingerprint="fingerprint-1",
        ),
    )

    assert result.action is RecoveryAction.ROLLBACK_STEP