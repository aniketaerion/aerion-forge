"""Application service for checkpoint and recovery control."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_runtime.checkpoints import (
    assert_checkpoint_valid,
)
from forge.autonomous_runtime.models import (
    AutonomousMission,
    MissionCheckpoint,
)
from forge.autonomous_runtime.recovery import (
    RecoveryContext,
    RecoveryEvaluation,
    choose_recovery_action,
)


@dataclass(frozen=True, slots=True)
class RecoveryRequest:
    """Recovery request for one failed mission step."""

    failure_class: str
    step_attempt_number: int
    rollback_attempt_number: int
    retryable: bool
    checkpoint: MissionCheckpoint | None = None
    mission_can_replan: bool = True
    expected_step_id: str | None = None
    expected_repository_fingerprint: str | None = None


class AutonomousRecoveryService:
    """Coordinate checkpoint validation and recovery selection."""

    def evaluate(
        self,
        mission: AutonomousMission,
        request: RecoveryRequest,
    ) -> RecoveryEvaluation:
        if request.checkpoint is not None:
            assert_checkpoint_valid(
                request.checkpoint,
                expected_mission_id=mission.mission_id,
                expected_step_id=request.expected_step_id,
                expected_repository_fingerprint=(
                    request.expected_repository_fingerprint
                ),
            )

        return choose_recovery_action(
            mission,
            RecoveryContext(
                failure_class=request.failure_class,
                step_attempt_number=(
                    request.step_attempt_number
                ),
                rollback_attempt_number=(
                    request.rollback_attempt_number
                ),
                retryable=request.retryable,
                checkpoint=request.checkpoint,
                mission_can_replan=request.mission_can_replan,
            ),
        )